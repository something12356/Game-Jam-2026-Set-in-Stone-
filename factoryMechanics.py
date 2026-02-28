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
        building = classes[buildingType]()
        cost = building.cost
        for oreCost in cost:
            for ore in self.ores:
                if ore.type == oreCost[1]:
                    if round(ore.amount, 2) >= oreCost[0]:
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
    def __init__(self, name, oreType, productionRate):
        self.name = name
        self.ore = oreType(0)
        self.productionRate = productionRate

    def mine(self):
        self.ore.amount += self.productionRate

class CopperMineBasic(Building):
    def __init__(self):
        super().__init__("Basic Copper Mine", Copper, 0.1)
        self.cost = [(3, "Copper")]

class CopperMineAdvanced(Building):
    def __init__(self):
        super().__init__("Advanced Copper Mine", Copper, 0.5)
        self.cost = [(10, "Copper"), (5, "Iron")]

class IronMine(Building):
    def __init__(self):
        super().__init__("Iron Mine", Iron, 0.1)
        self.cost = [(20, "Copper")]

## Have subclasses for different types of ores
class Ore:
    def __init__(self, amount, type, colour):
        self.amount = amount
        self.type = type
        self.colour = colour

class Copper(Ore):
    def __init__(self, amount):
        super().__init__(amount, "Copper", "orange")

class Iron(Ore):
    def __init__(self, amount):
        super().__init__(amount, "Iron", "grey")

classes = {"Iron":Iron, "Copper":Copper, "CopperMineBasic": CopperMineBasic, "CopperMineAdvanced":CopperMineAdvanced, "IronMine":IronMine}

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

