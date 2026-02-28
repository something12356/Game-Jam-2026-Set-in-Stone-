import pygame
import sys
import math

class Factory:
    def __init__(self, buildings: list[Building], ores: list[Ore]):
        self.buildings = buildings
        self.ores = ores

    def createBuilding(self, buildingType):
        if buildingType == "":
            return
        building = MINE_CLASSES[buildingType]()
        cost = building.cost
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

    ## Need to have "Collecting ore from buildings" as a feature rn its automatic? Or maybe not idk
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
    
# Add capability to mine multiple ores with same building
class Building:
    cost: list[tuple[int, str]]

    def __init__(self, name: str, oreType, productionRate):
        self.name = name
        self.ore: Ore = oreType(0)
        self.productionRate = productionRate

    def mine(self):
        self.ore.amount += self.productionRate

class CopperMineBasic(Building):
    cost = [(3, "Copper")]

    def __init__(self):
        super().__init__("Basic Copper Mine", Copper, 0.1)

class CopperMineAdvanced(Building):
    cost = [(10, "Copper"), (5, "Iron")]

    def __init__(self):
        super().__init__("Advanced Copper Mine", Copper, 0.5)

class IronMine(Building):
    cost = [(20, "Copper")]

    def __init__(self):
        super().__init__("Iron Mine", Iron, 0.1)

## Have subclasses for different types of ores
class Ore:
    def __init__(self, amount, type, colour):
        self.amount = amount
        self.type = type
        self.colour = colour

class Copper(Ore):
    def __init__(self, amount):
        super().__init__(amount, "Copper", (120, 58, 45))

class Iron(Ore):
    def __init__(self, amount):
        super().__init__(amount, "Iron", (61, 91, 114))

classes = {"Iron":Iron, "Copper":Copper, "CopperMineBasic": CopperMineBasic, "CopperMineAdvanced":CopperMineAdvanced, "IronMine":IronMine}
MINE_CLASSES = {"CopperMineBasic": CopperMineBasic, "CopperMineAdvanced":CopperMineAdvanced, "IronMine":IronMine}
RESOURCE_CLASSES = {"Iron":Iron, "Copper":Copper}

if __name__ == '__main__':
    factory1 = Factory([CopperMineBasic()], [Copper(2), Iron(0)])

    t=0
    while True:
        t+=1
        print(t)
        ## Only collect every 10 timesteps
        factory1.mineLoop(not(t%10))
        factory1.getOres()
        factory1.createBuilding(input("If you want to create a building type its name now\n"))
        print("---")
