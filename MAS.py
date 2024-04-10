import random
import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
import spade_bokeh
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Range1d
from bokeh.palettes import Greys9, OrRd9, Spectral11
from bokeh.io import curdoc
from spade.behaviour import FSMBehaviour, State
import asyncio
from spade.message import Message

class VacuumCleanerAgent(spade_bokeh.BokehServerMixin, Agent):
    def __init__(self, x, y, jid, password, port):
        super().__init__(jid, password)
        self.position = (x, y)
        self.directions = ['N', 'E', 'S', 'W']
        self.direction = random.choice(self.directions)
        self.color = (random.random(), random.random(), random.random())
        self.environment=None
        self.visited = set()
        self.port = port
        self.state_flag=None
    async def controller(self, request):
        script = self.bokeh_server.get_plot_script("/my_plot")

        return {"script": script}
    
    def modify_doc(self, doc):
        self.source = ColumnDataSource(data={
            'x': [],
            'y': [],
            'color': [],
        })

        plot = figure(title="Environment", 
                      x_range=Range1d(-0.5, len(self.environment.grid)-0.5), 
                      y_range=Range1d(-0.5, len(self.environment.grid[0])-0.5))
        plot.rect('x', 'y', 1, 1, source=self.source, color='color')

        self.agent_source = ColumnDataSource(data={
            'x': [],
            'y': [],
            'color': [],
        })
        plot.circle('x', 'y', source=self.agent_source, color='color', size=10)

        doc.add_root(plot)
        doc.add_periodic_callback(self.update_plot, 1)
        # self.update_plot()
    class BackgroundMessageReceiver(CyclicBehaviour):
        async def run(self):
            if self.agent.state_flag != 'Waiting' and self.agent.state_flag is not None:
                msg = await self.receive(timeout=10)
                if msg:
                    if msg.body.startswith("update:"):
                        tile_str = msg.body[len("update:"):].split(',')
                        if len(tile_str) == 2:
                            try:
                                new_tile = (int(tile_str[0]), int(tile_str[1]))
                                self.agent.visited.add(new_tile)
                                print(f"{self.agent.name} received a new tile from Blackboard: {new_tile} and updated the visited list.")
                                self.agent.state_flag='Moving'
                            except ValueError:
                                print(f"Error parsing tile coordinates from message: {msg.body}")
                        else:
                            print(f"Received message from Blackboard in unexpected format: {msg.body}")


                    elif msg.body.startswith("clean:"):
                        tile_str = msg.body[len("clean:"):].split(',')
                        if len(tile_str) == 2:
                            try:
                                new_tile = (int(tile_str[0]), int(tile_str[1]))
                                self.agent.visited.add(new_tile)
                                print(f"{self.agent.name} will start cleaning at {new_tile}.")
                                self.agent.state_flag='Cleaning'
                            except ValueError:
                                print(f"Error parsing tile coordinates from message: {msg.body}")
                        else:
                            print(f"Received message from Blackboard in unexpected format: {msg.body}")


    class CleanCycleBehaviour(FSMBehaviour):
        states = ["Moving", "Turning", "Cleaning", "Finished", "UpdateUnvisited", "WaitingState"]

        def __init__(self):
            super().__init__()
            self.add_state(name="Moving", state=self.Moving(), initial=True)
            self.add_state(name="Turning", state=self.Turning())
            self.add_state(name="UpdateUnvisited", state=self.UpdateUnvisitedTilesState())
            self.add_state(name="Cleaning", state=self.Cleaning())
            self.add_state(name="WaitingState", state=self.WaitingState())
            self.add_state(name="Finished", state=self.Finished())

            self.add_transition(source="Moving", dest="Turning")
            self.add_transition(source="Turning", dest="Moving")
            self.add_transition(source="Moving", dest="Cleaning")
            self.add_transition(source="WaitingState", dest="Cleaning")
            # self.add_transition(source="UpdateUnvisited", dest="Cleaning")
            self.add_transition(source="Moving", dest="UpdateUnvisited")
            self.add_transition(source="UpdateUnvisited", dest="WaitingState")
            self.add_transition(source="WaitingState", dest="Moving")
            self.add_transition(source="WaitingState", dest="WaitingState")
            self.add_transition(source="Cleaning", dest="Moving")
            self.add_transition(source="Cleaning", dest="Finished")
            self.add_transition(source="Moving", dest="Finished")
            self.add_transition(source="Turning", dest="Finished")
            self.add_transition(source="UpdateUnvisited", dest="Finished")
            self.add_transition(source="WaitingState", dest="Finished")

        class Moving(State):
            async def run(self):
                if self.agent.state_flag !='Moving' and self.agent.state_flag is not None:
                    self.set_next_state(self.agent.state_flag)
                    return
                print("Moving...")
                environment=self.agent.environment
                num_moves = random.randint(1, 5) 
                for _ in range(num_moves):
                    if self.agent.state_flag =='Moving' or self.agent.state_flag is None:
                        next_x = self.agent.position[0]
                        next_y = self.agent.position[1]
                        if self.agent.direction == 'N':
                            next_y += 1
                        elif self.agent.direction == 'E':
                            next_x += 1
                        elif self.agent.direction == 'S':
                            next_y -= 1
                        elif self.agent.direction == 'W':
                            next_x -= 1
                        if not environment.is_obstacle((next_x, next_y), self.agent.direction) and not environment.grid[next_x][next_y].is_obstacle and not any(agent.position == (next_x, next_y) for agent in environment.agents):
                            if (next_x, next_y) not in self.agent.visited and not (next_x == 0 or next_x == n or next_y == 0 or next_y == m):
                                print("Condition to transition to UpdateUnvisited met.")
                                self.agent.position = (next_x, next_y)
                                # self.agent.visited.add((next_x, next_y))
                                print(f'moved to {next_x} {next_y}')
                                self.agent.schedule_update()
                                await asyncio.sleep(0.5)
                                self.set_next_state("UpdateUnvisited")
                                break
                            self.agent.position = (next_x, next_y)
                            # self.agent.visited.add((next_x, next_y))
                            print(f'moved to {next_x} {next_y}')
                            self.agent.schedule_update()
                            self.agent.state_flag= None
                            await asyncio.sleep(0.5)


                        else:
                            print(f"Can't move to {next_x} {next_y}, it's an obstacle or occupied by another agent. Turning right.")
                            self.agent.state_flag= None
                            self.set_next_state("Turning")
                            break

                        if environment.is_dirty(self.agent.position):
                            self.set_next_state("Cleaning")
                            self.agent.state_flag= None
                            break
                        else:
                            self.agent.state_flag= None
                            self.set_next_state("Turning")
                    else:
                        self.set_next_state(self.agent.state_flag)
                        break

        class Turning(State):
            async def run(self):
                print("Turning...")
                if self.agent.direction == 'N':
                    self.agent.direction = 'E'
                elif self.agent.direction == 'E':
                    self.agent.direction = 'S'
                elif self.agent.direction == 'S':
                    self.agent.direction = 'W'
                elif self.agent.direction == 'W':
                    self.agent.direction = 'N'
                self.agent.state_flag= None
                self.set_next_state("Moving")

        class Cleaning(State):
            async def run(self):
            #     if self.agent.state_flag!='Cleaning':
            #         self.set_next_state(self.agent.state_flag)
                print("Cleaning...")
                environment=self.agent.environment
                if environment.is_dirty(self.agent.position):
                    environment.clean_tile(self.agent.position)
                    print(f"Sucked dirt at position {self.agent.position}")
                    self.agent.environment.grid[self.agent.position[0]][self.agent.position[1]].color = Greys9[5]
                self.agent.schedule_update()
                self.agent.state_flag= None
                # await asyncio.sleep(0.5)
                dirty_tiles = [(i, j) for i in range(len(environment.grid)) for j in range(len(environment.grid[0])) if environment.is_dirty((i, j))]
                if not dirty_tiles and len(self.agent.environment.blackboard.visited_tiles) == len(self.agent.environment.is_accessible):
                    self.set_next_state("Finished")
                    for agent in environment.agents:
                        self.agent.state_flag= None
                        await agent.stop()
                    blackboard_agent.stop()
                else:
                    self.set_next_state("Moving")
                    self.agent.state_flag= None
        class UpdateUnvisitedTilesState(State):
            async def run(self):
                print("Entered UpdateUnvisited met.")
                if self.agent.position not in self.agent.visited:
                    is_dirty = "1" if self.agent.environment.is_dirty(self.agent.position) else "0"
                    serialized_position = f"{self.agent.position[0]},{self.agent.position[1]},{is_dirty}"
                    msg = Message(to="blackboard@localhost")
                    msg.body = serialized_position
                    print(f"Agent {self.agent.name}: Sent new visited tile and dirtiness to Blackboard.")
                    await self.send(msg)
                    self.agent.state_flag='Waiting'
                self.set_next_state('WaitingState')
        class WaitingState(State):
            async def run(self):
                if self.agent.state_flag=='Waiting':
                    print(f"{self.agent.name} is waiting for an update from Blackboard...")
                    msg = await self.receive(timeout=10)
                    if msg and msg.body.startswith("update:"):
                        tile_str = msg.body[len("update:"):].split(',')
                        if len(tile_str) == 2:
                            try:
                                new_tile = (int(tile_str[0]), int(tile_str[1]))
                                self.agent.visited.add(new_tile)
                                print(f"{self.agent.name} received a new tile from Blackboard: {new_tile} and updated the visited list.")
                            except ValueError:
                                print(f"Error parsing tile coordinates from message: {msg.body}")
                        else:
                            print(f"Received message from Blackboard in unexpected format: {msg.body}")
                        self.agent.state_flag='Moving'
                        self.set_next_state("Moving")
                    elif msg and msg.body.startswith("clean:"):
                        tile_str = msg.body[len("clean:"):].split(',')
                        if len(tile_str) == 2:
                            try:
                                new_tile = (int(tile_str[0]), int(tile_str[1]))
                                self.agent.visited.add(new_tile)
                                print(f"{self.agent.name} will start cleaning--------.")
                                self.agent.state_flag='Cleaning'
                                self.set_next_state("Cleaning")
                            except ValueError:
                                print(f"Error parsing tile coordinates from message: {msg.body}")
                        else:
                            print(f"Received message from Blackboard in unexpected format: {msg.body}")
                        

                    else:

                        print(f"{self.agent.name} did not receive any new tile updates. Deciding next action...")
                        self.agent.state_flag='Waiting'
                        self.set_next_state("Waiting")
                
        
        class Finished(State):
            async def run(self):
                print("Finished cleaning.")

        async def on_end(self):
            print("Clean cycle behaviour ended.")




    def update_plot(self):
        data = {
            'x': [],
            'y': [],
            'color': [],
        }
        for i, row in enumerate(self.environment.grid):
            for j, tile in enumerate(row):
                data['x'].append(i)
                data['y'].append(j)
                if tile.is_obstacle:
                    data['color'].append(Spectral11[0])
                elif tile.is_dirty:
                    data['color'].append(OrRd9[4])
                else:
                    data['color'].append(Greys9[5])
        self.source.data = data 


        agent_data = {
            'x': [agent.position[0] for agent in self.environment.agents if isinstance(agent, VacuumCleanerAgent)],
            'y': [agent.position[1] for agent in self.environment.agents if isinstance(agent, VacuumCleanerAgent)],
            'color': [agent.color for agent in self.environment.agents if isinstance(agent, VacuumCleanerAgent)],
        }
        self.agent_source.data = agent_data 

    def schedule_update(self):
        curdoc().add_next_tick_callback(self.update_plot)

    async def setup(self):
        print(f"Agent starting with port {self.port}")
        clean_cycle_behaviour = self.CleanCycleBehaviour()
        background_message_receiver= self.BackgroundMessageReceiver()
        self.add_behaviour(background_message_receiver)
        self.add_behaviour(clean_cycle_behaviour)

        self.source = ColumnDataSource(data={
            'x': [],
            'y': [],
            'color': [],
        })
        self.agent_source = ColumnDataSource(data={
            'x': [],
            'y': [],
            'color': [],
        })

        self.web.add_get("/plot", self.controller, "plot.html")
        self.web.start(hostname="127.0.0.1",port=10015)
        self.bokeh_server.start()
        self.bokeh_server.add_plot("/my_plot", self.modify_doc)
        self.update_plot()



class Tile:
    def __init__(self, is_dirty=False, is_obstacle=False):
        self.is_dirty = is_dirty
        self.is_obstacle = is_obstacle

class Environment:
    def __init__(self, n, m, x, y, agents, blackboard):
        self.grid = [[Tile() for _ in range(m)] for _ in range(n)]
        self.agents = agents
        self.blackboard=blackboard
        self.obstacles = []

        for _ in range(x):
            obstacle_size = random.randint(1, 3)
            start_x = random.randint(1, n - 2)
            start_y = random.randint(1, m - 2)
            direction = random.choice([(0, 1), (1, 0)])

            for i in range(obstacle_size):
                obstacle_x = start_x + i * direction[0]
                obstacle_y = start_y + i * direction[1]

                if 1 <= obstacle_x < n - 1 and 1 <= obstacle_y < m - 1:
                    self.obstacles.append((obstacle_x, obstacle_y))
                    self.grid[obstacle_x][obstacle_y].is_obstacle = True
                    possible_dirty_tiles=0
                    possible_dirty_tiles = [(i, j) for i in range(1, n-1) for j in range(1, m-1) if (i, j) not in [agent.position for agent in agents] + self.obstacles]
        self.dirty_tiles = random.sample(possible_dirty_tiles, y)
        for tile in self.dirty_tiles:
            self.grid[tile[0]][tile[1]].is_dirty = True
        self.is_accessible = lambda grid, n, m: sum(
    1 for i, row in enumerate(grid) for j, tile in enumerate(row)
    if not tile.is_obstacle and not (i == 0 or i == n-1 or j == 0 or j == m-1)
)



    def is_dirty(self, position):
        return self.grid[position[0]][position[1]].is_dirty

    def clean_tile(self, position):
        self.grid[position[0]][position[1]].is_dirty = False

    def is_obstacle(self, position, direction):
        next_x = position[0]
        next_y = position[1]
        if direction == 'N':
            next_y += 1
        elif direction == 'E':
            next_x += 1
        elif direction == 'S':
            next_y -= 1
        elif direction == 'W':
            next_x -= 1
        return (next_x, next_y) in self.obstacles or next_x < 0 or next_y < 0 or next_x >= len(self.grid) or next_y >= len(self.grid[0]) or any(agent.position == (next_x, next_y) for agent in self.agents if agent != self)

class BlackboardAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.environment=None
        self.visited_tiles = set()
    
    class BlackboardBehaviour(FSMBehaviour):
        class WaitState(State):
            async def run(self):
                msg = await self.receive(timeout=10)
                if msg:
                    self.agent.msg=msg
                    self.set_next_state("ReceiveTileState")

        class ReceiveTileState(State):
            async def run(self):
                msg=self.agent.msg
                # msg = await self.receive(timeout=10)
                if msg:
                    parts = msg.body.split(',')
                    new_tile = tuple(map(int, parts[:2]))
                    is_dirty = parts[2] == "1"
                    self.agent.new_tile = new_tile
                    self.agent.tile_dirty = is_dirty
                    self.agent.msg_sender = msg.sender
                    self.agent.visited_tiles.add(new_tile)
                    print(f"Blackboard received new tile: {new_tile} with dirtiness status {is_dirty}")
                    self.set_next_state("SendTileState")

        class SendTileState(State):
            async def run(self):
                if hasattr(self.agent, "new_tile"):
                    serialized_tile = f"{self.agent.new_tile[0]},{self.agent.new_tile[1]}"
                    coroutines = [] 

                
                    if self.agent.tile_dirty:
                        msg_to_sender = Message(to=str(self.agent.msg_sender))
                        msg_to_sender.body = f"clean:{serialized_tile}"
                        coroutines.append(self.send(msg_to_sender))
                        print(f"Message sent to the original sender: {self.agent.msg_sender}")

                        for agent_jid in self.agent.agent_jids:
                            if str(agent_jid) != str(self.agent.msg_sender):
                                msg = Message(to=str(agent_jid))
                                msg.body = f"update:{serialized_tile}"
                                coroutines.append(self.send(msg))
                    else:
                        for agent_jid in self.agent.agent_jids:
                            msg = Message(to=str(agent_jid))
                            msg.body = f"update:{serialized_tile}"
                            coroutines.append(self.send(msg))

                    await asyncio.gather(*coroutines)

                    print("Blackboard broadcasted the new tile and instructions to agents")

                    self.set_next_state("WaitState")



        def __init__(self):
            super().__init__()
            self.add_state(name="WaitState", state=self.WaitState(), initial=True)
            self.add_state(name="ReceiveTileState", state=self.ReceiveTileState())
            self.add_state(name="SendTileState", state=self.SendTileState())

            self.add_transition(source="WaitState", dest="ReceiveTileState")
            self.add_transition(source="ReceiveTileState", dest="SendTileState")
            self.add_transition(source="SendTileState", dest="WaitState")


    def __init__(self, jid, password, agent_jids):
        super().__init__(jid, password)
        self.visited_tiles = set()
        self.agent_jids = agent_jids

    async def setup(self):
        print(f"Agent starting with port 20100")
        blackboard_behaviour = self.BlackboardBehaviour()
        self.add_behaviour(blackboard_behaviour)


PASSWORD = 'PASSWORD'
DIRECTIONS = {
    'N': (0, 1),
    'E': (1, 0),
    'S': (0, -1),
    'W': (-1, 0),
}
def generate_agents(x, n, m):
    agents = []
    for i in range(x):
        start_x = random.randint(1, n-1)
        start_y = random.randint(1, m-1)
        jid = f'user{i+1}@localhost'
        port = 20000 + i
        agent = VacuumCleanerAgent(start_x, start_y, jid, PASSWORD, port)
        agents.append(agent)
    return agents



if __name__ == "__main__":
    n = 10 
    m = 10
    x = 5  
    y = 10  
    agents = generate_agents(3, n, m)

    agent_jids = list()
    blackboard_agent = BlackboardAgent("blackboard@localhost", PASSWORD, agent_jids)
    environment = Environment(n, m, x, y, agents, blackboard_agent)
    blackboard_agent.environment=environment
    for agent in agents:
        agent_jids.append(agent.jid)
    for agent in agents:
        agent.environment = environment
    async def start_agents():
        coroutines = [agent.start() for agent in agents]
        coroutines.insert(0, blackboard_agent.start())
        await asyncio.gather(*coroutines)

    asyncio.run(start_agents())

    print("Simulation finished.")