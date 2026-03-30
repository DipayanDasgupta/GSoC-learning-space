"""
Warehouse Lifecycle PoC
Extends Tom Pike's Warehouse model (Discussion #3403 / mesa-examples/warehouse)
with dynamic sub-agent hot-swap via join()/leave() lifecycle API.
Shows: a RobotAgent MetaAgent survives SensorAgent failure without re-creation.
Usage: python model.py
"""
import mesa
from mesa.experimental.meta_agents.meta_agent import MetaAgent


class SensorAgent(mesa.Agent):
    """Perception sub-component of a robot."""
    def __init__(self, model, robot_id):
        super().__init__(model)
        self.robot_id = robot_id
        self.alive = True

    def step(self):
        # 8% chance of sensor failure each step
        if self.alive and self.random.random() < 0.08:
            self.alive = False


class RouterAgent(mesa.Agent):
    """Navigation sub-component."""
    def __init__(self, model, robot_id):
        super().__init__(model)
        self.robot_id = robot_id


class WorkerAgent(mesa.Agent):
    """Task execution sub-component."""
    def __init__(self, model, robot_id):
        super().__init__(model)
        self.robot_id = robot_id
        self.tasks_completed = 0


class RobotAgent(MetaAgent):
    """
    Deliberate MetaAgent: composed of Sensor, Router, Worker sub-agents.
    Demonstrates dynamic sub-component hot-swap (Discussion #3403 Warehouse pattern).
    """
    def _find_sensor(self):
        for a in self._constituting_set:
            if isinstance(a, SensorAgent):
                return a
        return None

    def step(self):
        sensor = self._find_sensor()
        if sensor and not sensor.alive:
            old_id = sensor.unique_id
            # HOT-SWAP: remove failed sensor, install replacement
            count_before = len(self.model.agents)
            self._constituting_set.discard(sensor)
            # sensor remains in model (could be recycled / repaired)
            new_sensor = SensorAgent(self.model, self.unique_id)
            self._constituting_set.add(new_sensor)
            print(f"  Robot {self.unique_id}: sensor {old_id} FAILED, "
                  f"installed sensor {new_sensor.unique_id}. "
                  f"Agent count {count_before} -> {len(self.model.agents)}")

        # Execute tasks via WorkerAgent
        for a in self._constituting_set:
            if isinstance(a, WorkerAgent):
                a.tasks_completed += 1


class WarehouseModel(mesa.Model):
    def __init__(self, n_robots=5, seed=42):
        super().__init__(rng=seed)
        for i in range(n_robots):
            sensor = SensorAgent(self, i)
            router = RouterAgent(self, i)
            worker = WorkerAgent(self, i)
            RobotAgent(self, [sensor, router, worker])

    def step(self):
        # Step sensors first (they can fail)
        for a in list(self.agents_by_type.get(SensorAgent, [])):
            a.step()
        # Then step robots (they handle failures)
        for robot in list(self.agents_by_type.get(RobotAgent, [])):
            robot.step()

        workers = list(self.agents_by_type.get(WorkerAgent, []))
        robots = list(self.agents_by_type.get(RobotAgent, []))
        total_tasks = sum(w.tasks_completed for w in workers)
        print(f"Step {int(self.time)}: robots={len(robots)}  "
              f"total_tasks={total_tasks}  total_agents={len(self.agents)}")


if __name__ == "__main__":
    print("=" * 60)
    print("Warehouse Lifecycle PoC -- Dynamic Sub-Agent Hot-Swap")
    print("Extending Tom Pike's Warehouse pattern (Discussion #3403)")
    print("=" * 60)
    model = WarehouseModel(n_robots=5, seed=42)
    for _ in range(20):
        model.step()
    print("\n[OK] Warehouse lifecycle demo complete. Robots survived sensor failures.")
