import pygame

class Factory:
    def __init__(self, buildings):
        self.buildings = buildings

    def createBuilding(self, name, oreType, productionRate):
        building = Building(name, oreType, productionRate)
        self.buildings.append(building)

    def mineLoop(self):
        for building in self.buildings:
            building.mine()

    def getOres(self):
        oreDict = {building.ore.type : 0 for building in self.buildings}
        for building in self.buildings:
            oreDict[building.ore.type] += building.ore.amount
            print(f'{building.name} | {building.ore.type} | {building.ore.amount}')
        
        print()
        for i in oreDict:
            print(f'Total {i} | {oreDict[i]}')
    
# Add capability to mine multiple ores with same building
class Building:
    def __init__(self, name, oreType, productionRate):
        self.name = name
        self.ore = Ore(0, oreType)
        self.productionRate = productionRate

    def mine(self):
        self.ore.amount += self.productionRate

## Have subclasses for different types of ores
class Ore:
    def __init__(self, amount, type):
        self.amount = amount
        self.type = type

factory1 = Factory([])

factory1.createBuilding("building1", "ore1", 1)
factory1.createBuilding("building2", "ore2", 2)
factory1.createBuilding("building3", "ore1", 3)

while True:
    factory1.mineLoop()
    factory1.getOres()
    input("---")

