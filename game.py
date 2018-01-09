import pygame
import pygame.time
import serial
from serial.tools import list_ports
import time
import sys
sys.path.insert(0, '/Projects/psmoveapi/build');
import psmove

##

class Node(object):

    def __init__(self, pixelCount):
        self.lines = []
        self.pixels = []

        for i in range(pixelCount):
            self.pixels.append(Pixel())

    def addLine(self, line):
        self.lines.append(line)

    def getPixelData(self):
        return [pixel.getData() for pixel in self.pixels]

    def setPlayerAt(self, color):
        for pixel in self.pixels:
            pixel.setNodeHighlight(color)

    def removePlayerFrom(self, color):
        for pixel in self.pixels:
            pixel.unsetNodeHighlight(color)

##

class Line(object):                        
   
    def __init__(self, pixelCount):
        self.pixels = []
        for i in range(pixelCount):
            self.pixels.append(Pixel())

    def setNode1(self, node):
        self.node1 = node

    def setNode2(self, node):
        self.node2 = node

    def getPixelData(self):
        return [pixel.getData() for pixel in self.pixels]

    def setPlayerAt(self, index, color):
        if (index < 0):
            return self.node1
        elif (index >= len(self.pixels)):
            return self.node2
        else:
            self.pixels[index].setLineHighlight(color)
            return None

    def removePlayerFrom(self, index, color):
        self.pixels[index].unsetLineHighlight(color)

    def setPointer(self, color, node):
        pixel = self.pixels[0] if node == self.node1 else self.pixels[-1]
        pixel.setLinePointer(color) 

    def unsetPointer(self, color, node):
        pixel = self.pixels[0] if node == self.node1 else self.pixels[-1]
        pixel.unsetLinePointer(color)         

    def getDirectionFromNode(self, node):
        return 1 if node == self.node1 else -1

    def getFirstPixelIndexFromNode(self, node):
        return 0 if node == self.node1 else len(self.pixels)-1

    def update(self):
        for pixel in self.pixels:
            pixel.fade()

##

class Pixel(object):
    
    def __init__(self):
        self.color = 0
        self.colorOverride = None
        self.alpha = 0
        self.alphaOverride = None

    def getData(self):
        color = self.color if self.colorOverride is None else self.colorOverride
        alpha = self.alpha if self.alphaOverride is None else self.alphaOverride
        return (color << 6) + round(alpha*63)

    def setLineHighlight(self, color):
        self.color = color
        self.alpha = 1

    def unsetLineHighlight(self, color):
        self.alpha = 0.5

    def setNodeHighlight(self, color):
        self.color = color
        self.alpha = 1

    def unsetNodeHighlight(self, color):
        self.color = color
        self.alpha = 0.5

    def setLinePointer(self, color):
        self.colorOverride = 2
        self.alphaOverride = 1

    def unsetLinePointer(self, color):
        self.colorOverride = None
        self.alphaOverride = None

    def fade(self):
        self.alpha -= 0.005
        if (self.alpha < 0):
            self.alpha = 0

##

class Player(object):

    def __init__(self, startingNode, color):
        self.color = color
        self.currentLine = None
        self.currentLineIndex = 0
        self.currentLineDirection = 1
        self.currentNode = startingNode
        self.currentNodeExitIndex = 0
        self.moveAccum = 0  #ticks up per frame, and movement happens when it's high enough

        self.currentNode.setPlayerAt(color)
        self.currentNode.lines[self.currentNodeExitIndex].setPointer(self.color, self.currentNode)

    def update(self):
        if (self.currentLine is not None):
            self.moveAccum += 2
            if (self.moveAccum == 20):
                self.moveAccum = 0
                self.currentLine.removePlayerFrom(self.currentLineIndex, self.color)
                self.currentLineIndex += self.currentLineDirection
                atNode = self.currentLine.setPlayerAt(self.currentLineIndex, self.color)
                if (atNode is not None):
                    # Arrive at node
                    self.currentLine = None
                    self.currentNode = atNode
                    self.currentNode.setPlayerAt(self.color)
                    self.currentNodeExitIndex = -1
                    #self.currentNode.lines[self.currentNodeExitIndex].setPointer(self.color, self.currentNode)

    def advanceNodeExit(self):
        if self.currentNode:
            if self.currentNodeExitIndex is not None:
                self.currentNode.lines[self.currentNodeExitIndex].unsetPointer(self.color, self.currentNode)
            self.currentNodeExitIndex += 1
            self.currentNodeExitIndex %= len(self.currentNode.lines)
            self.currentNode.lines[self.currentNodeExitIndex].setPointer(self.color, self.currentNode)

    def goNodeExit(self):
        if self.currentNode and self.currentNodeExitIndex >= 0:
            # Leave node
            self.currentLine = self.currentNode.lines[self.currentNodeExitIndex]
            self.currentLineDirection = self.currentLine.getDirectionFromNode(self.currentNode)
            self.currentLineIndex = self.currentLine.getFirstPixelIndexFromNode(self.currentNode)
            self.currentNode.lines[self.currentNodeExitIndex].unsetPointer(self.color, self.currentNode)
            self.currentNode = None
            self.moveAccum = 0

##

def getStrandPixels(strand):
    pixels = []
    for thing in strand:
        pixels += thing.pixels
    return pixels


def connectStrand(things):
    lastNode = things[0]
    for i in range(0, len(things)-2, 2):
        node1 = things[i]
        line = things[i+1]
        node2 = things[i+2]

        node1.addLine(line)
        node2.addLine(line)
        line.setNode1(node1)
        line.setNode2(node2)
    return things


def connectNodesToLine(node1, node2, line):
    node1.addLine(line)
    node2.addLine(line)
    line.setNode1(node1)
    line.setNode2(node2)






### STRAND CONFIG
nodes = [Node(1), Node(1), Node(1), Node(1), Node(1)]
lines = [Line(14), Line(13), Line(14), Line(13)]

strands = [
    connectStrand([nodes[0], lines[0], nodes[1], lines[1], nodes[2]]),
    connectStrand([nodes[3], lines[2], nodes[1], lines[3], nodes[4]])
]

startingNodes = [nodes[0], nodes[1]]
### 

### PSMOVE CONFIG
moves = [psmove.PSMove(x) for x in range(psmove.count_connected())]
###

### PLAYER CONFIG
player = Player(nodes[0], 0)
###

print("\n\n", [port.device for port in list_ports.comports()], "\n\n")
ser = serial.Serial('/dev/cu.wchusbserial1460', 115200)

time.sleep(2) # the serial connection resets the arduino, so give the program time to boot

pygame.init()
clock = pygame.time.Clock()

while True:
    clock.tick(30)

    player.update()

    for line in lines:
        line.update()

    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                player.advanceNodeExit()
            elif event.key == pygame.K_SPACE:
                player.goNodeExit()

    pixelData = []
    for strand in strands:
        pixelData += [pixel.getData() for pixel in getStrandPixels(strand)]

    print(pixelData)

    ser.write(bytes(pixelData))
    ser.flush()

    print(ser.readline())

