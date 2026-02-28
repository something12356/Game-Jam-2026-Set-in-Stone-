import pygame
import sys
import math

class Contract:
    ## Party1 and party2 are the two players signing the contract
    ## (Party1, party2 will just be the factories associated with the players)
    ## Term1 is what party1 owes to party2
    ## Term2 is what party2 owes to party1
    ## Time limit is when the contract must be fulfilled by
    def __init__(self, party1, party2, terms1, terms2, timeLimit):
        self.party1 = party1
        self.party2 = party2
        self.terms1 = terms1
        self.terms2 = terms2
        self.timeLimit = timeLimit

    ## Currently assuming all terms are just to do with ores, might want to update later to include other items
    ## So the term format will be same as cost format for buildings at the moment
    ## (If we decide to introduce other items)
    def checkFulfilled(self):
        print(self.terms1, self.terms2)
        for term in self.terms1:
            for ore1 in self.party1.ores:
                if ore1.type == term[1]:
                    if round(ore1.amount, 3) >= term[0]:
                        ore1.amount -= term[0]
                        for ore2 in self.party2.ores:
                            if ore2.type == term[1]:
                                ore2.amount += term[0]
                    else:
                        print("Party 1 has failed to fulfill the contract!")

        for term in self.terms2:
            for ore2 in self.party2.ores:
                if ore2.type == term[1]:
                    if round(ore2.amount, 3) >= term[0]:
                        ore2.amount -= term[0]
                        for ore1 in self.party1.ores:
                            if ore1.type == term[1]:
                                ore1.amount += term[0]
                    else:
                        print("Party 2 has failed to fulfill the contract!")


## Each player will have their own factory
class Factory:
    def __init__(self, buildings: list[Building], ores: list[Ore], capacity: int):
        self.buildings = buildings
        self.ores = ores
        self.capacity = capacity

    # Creates building based on what player selects and if they have enough ores to buy it + if they are not above the current building limit
    def createBuilding(self, buildingType):
        if buildingType == "":
            return
        building = MINE_CLASSES[buildingType]()
        cost = building.cost
        if (len(self.buildings) >= self.capacity):
            print("You have reached the maximum build limit")
            return
        for oreCost in cost:
            for ore in self.ores:
                if ore.type == oreCost[1]:
                    if round(ore.amount, 3) >= oreCost[0]:
                        continue
                    else:
                        print("You cannot afford this!")
                        return
        for oreCost in cost:
            for ore in self.ores:
                if ore.type == oreCost[1]:
                    ore.amount -= oreCost[0]
        self.buildings.append(building)

    ## All the buildings mine their ores, collects ore from building periodically
    def mineLoop(self, collecting=False):
        for building in self.buildings:
            building.mine()

        oreDict = {building.ore.type : 0 for building in self.buildings}
        for building in self.buildings:
            oreDict[building.ore.type] += building.ore.amount

        if collecting:
            for ore in self.ores:
                if ore.type in oreDict:
                    ore.amount += oreDict[ore.type]

            for building in self.buildings:
                building.ore.amount = 0

    def getOres(self):
        for building in self.buildings:
            print(f'{building.name} | {building.ore.type} | {building.ore.amount:.2f}')

        print('')
        for i in self.ores:
            print(f'Total {i.type} | {i.amount:.2f}')


## Have subclasses for different types of ores
class Ore:
    name: str

    def __init__(self, amount, type, colour):
        self.amount = amount
        self.type = type
        self.colour = colour

class Copper(Ore):
    name = 'Copper'

    def __init__(self, amount):
        super().__init__(amount, "Copper", (120, 58, 45))

class Iron(Ore):
    name = 'Iron'

    def __init__(self, amount):
        super().__init__(amount, "Iron", (61, 91, 114))

class NullResource(Ore):
    name = "NullResource"

    def __init__(self, amount):
        super().__init__(amount, "NullResource", (0, 0, 0))

# Add capability to mine multiple ores with same building
class Building:
    cost: list[tuple[int, str]]
    name: str
    produces: type[Ore]
    productionRate: float
    can_buy_directly: bool = True

    def __init__(self, name: str, oreType, productionRate):
        self.name = name
        self.ore: Ore = oreType(0)
        self.productionRate = productionRate

    def mine(self):
        self.ore.amount += self.productionRate

class BlockedSlot(Building):
    cost = [(0, "NullResource")]
    name = "(Blocked Slot)"
    produces = NullResource
    productionRate = 0
    can_buy_directly = False

    def __init__(self):
        super().__init__("BlockedSlot", NullResource, 0)

class CopperMineBasic(Building):
    cost = [(3, "Copper")]
    name = 'Basic Copper Mine'
    produces = Copper
    productionRate = 0.1

    def __init__(self):
        super().__init__("Basic Copper Mine", Copper, 0.1)


class CopperMineAdvanced(Building):
    cost = [(10, "Copper"), (5, "Iron")]
    name = 'Advanced Copper Mine'
    produces = Copper
    productionRate = 0.5

    def __init__(self):
        super().__init__("Advanced Copper Mine", Copper, 0.5)

class IronMine(Building):
    cost = [(20, "Copper")]
    name = 'Iron Mine'
    produces = Iron
    productionRate = 0.1

    def __init__(self):
        super().__init__("Iron Mine", Iron, 0.1)


classes = {"Iron":Iron, "Copper":Copper, "CopperMineBasic": CopperMineBasic, "CopperMineAdvanced":CopperMineAdvanced, "IronMine":IronMine, "Block":BlockedSlot}
MINE_CLASSES = {"CopperMineBasic": CopperMineBasic, "CopperMineAdvanced":CopperMineAdvanced, "IronMine":IronMine, "BlockedSlot": BlockedSlot}
RESOURCE_CLASSES = {"Iron":Iron, "Copper":Copper, "NullResource": NullResource}

if __name__ == '__main__':
    factory1 = Factory([CopperMineBasic()], [Copper(2), Iron(0)], 10)
    factory2 = Factory([CopperMineBasic()], [Copper(2), Iron(0)], 10)
    contracts = [Contract(factory1, factory2, [(3, "Copper"), (1, "Iron")], [(2, "Copper")], 130)]

    t=0
    while True:
        t+=1
        print(t)

        print("Player 1:\n")
        ## Only collect every 10 timesteps
        ## Turn this whole thing into a function so we can easily run it for multiple players
        factory1.mineLoop(not(t%10))
        factory1.getOres()
        factory1.createBuilding(input("If you want to create a building type its name now\n"))

        print("Player 2:\n")
        factory2.mineLoop(not(t%10))
        factory2.getOres()
        factory2.createBuilding(input("If you want to create a building type its name now\n"))

        for contract in contracts:
            if t >= contract.timeLimit:
                contract.checkFulfilled()

        print("---")
