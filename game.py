import pygame
import pygame.time
import random
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

    def pulse(self):
        for pixel in self.pixels:
            pixel.pulse()

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

    def isIndexAtNode(self, index):
        if (index < 0):
            return self.node1
        elif (index >= len(self.pixels)):
            return self.node2
        else:
            return None

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

##

class Pixel(object):
    
    def __init__(self):
    	self.reset()

    def reset(self):
    	self.color = 0
        self.colorOverride = None
        self.alpha = 0
        self.alphaOverride = None
        self.player = None
        self.powerup = False
        self.pulseTicker = 0;

    def getData(self):
        color = self.color if self.colorOverride is None else self.colorOverride
        alpha = self.alpha if self.alphaOverride is None else self.alphaOverride
        return (color << 5) + round(alpha*31)

    def setPlayer(self, player, alpha):
        self.player = player
        self.color = player.color
        self.alpha = alpha

    def unsetPlayer(self):
        self.player = None
        self.color = 0

    def setLinePointer(self, color):
        self.colorOverride = 5
        self.alphaOverride = 1

    def unsetLinePointer(self, color):
        self.colorOverride = None
        self.alphaOverride = None

    def setPowerup(self):
    	self.powerup = True
    	self.color = 6

	def unsetPowerup(self):
		self.powerup = False
		self.color = 0

    def pulse(self):
        self.alpha = 0.5 + (self.pulseTicker % 100)/200
        self.pulseTicker += 1
        # This does not need to be "undone" when a player leaves this pixel, because setPlayer is set on every pixel in a player's length on every frame

##

class Player(object):

    def __init__(self, startingNode, colorId, colorValue, move):
    	self.startingNode = startingNode
        self.color = colorId
        self.colorValue = colorValue
        self.move = move
        self.reset()

    def reset(self):
    	self.currentLine = None
        self.currentLineIndex = 0
        self.currentLineDirection = 1
        self.currentNode = startingNode
        self.currentNodeExitIndex = 0
        self.moveAccum = 0  #ticks up per frame, and movement happens when it's high enough
        self.pixels = [self.startingNode.pixels] #each element is a set of pixels, since nodes have 2 pixels
        self.length = 1
        self.alive = False
        self.ready = False # for starting the game

        #self.advanceToPixels(self.currentNode.pixels)
        #self.currentNode.lines[self.currentNodeExitIndex].setPointer(self.color, self.currentNode)

        self.move.set_leds(0, 0, 0)
        self.move.update_leds()

    def update(self):
    	if not self.alive:
    		return

        # Controls
        while self.move.poll():
            pressed, released = self.move.get_button_events()
            if pressed & psmove.Btn_T:
                self.goNodeExit()
            elif pressed & (psmove.Btn_TRIANGLE | psmove.Btn_CIRCLE | psmove.Btn_SQUARE | psmove.Btn_CROSS | psmove.Btn_MOVE):
                self.advanceNodeExit()

        # Movement
        if self.currentLine is not None:
            self.moveAccum += 2
            if (self.moveAccum == 20):
                self.moveAccum = 0
                self.currentLineIndex += self.currentLineDirection
                atNode = self.currentLine.isIndexAtNode(self.currentLineIndex)
                if atNode is None:
                    self.advanceToPixels(self.currentLine.pixels[self.currentLineIndex])
                else:
                    # Arrive at node
                    self.currentLine = None
                    self.currentNode = atNode
                    self.currentNodeExitIndex = -1
                    self.advanceToPixels(self.currentNode.pixels)

        # Staying still at a node
        if self.currentNone is not None:
            self.currentNode.pulse()

    def updateOutOfGame(self):
    	while move.poll():
    		self.ready = move.get_trigger() > 0
    		pressed, released = self.move.get_button_events()
    		if (pressed & psmove.Btn_MOVE):
    			self.alive = not self.alive
    			if self.alive:
    				self.move.set_leds(colorValue[0], colorValue[1], colorValue[2])
    				self.advanceToPixels(self.currentNode.pixels)
    			else:
    				self.move.set_leds(0, 0, 0)
    				self.removeFromAllPixels()
        		self.move.update_leds()


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

    def powerup(self):
    	self.length += 2

    def kill(self):
        self.alive = False
        self.removeFromAllPixels()
        self.move.set_leds(0, 0, 0)
        self.move.update_leds()

    def collideWith(self, player):
        if self.pixels[-1][0] == player.pixels[-1][0]: 
            # head on collision
            if self.length >= player.length
                player.kill()
            if self.length <= player.length
                self.kill()
        else:
            self.kill()

    def advanceToPixels(self, newPixels):
        if not isinstance(newPixels, list):
            newPixels = [newPixels]

        # Collision?
        for pixel in newPixels:
            if pixel.player is not None and pixel.player != self:
                self.collideWith(pixel.player)
                if not self.alive:
                    return;

        # Powerup?
        for pixel in newPixels:
        	if pixel.powerup:
        		self.powerup()
        		pixel.unsetPowerup()

        self.pixels.append(newPixels);

        if (len(self.pixels) > self.length):
            oldPixelSet = self.pixels[1]
            self.pixels = self.pixels[1:]
            for pixel in oldPixelSet:
                pixel.unsetPlayer()

        for i, pixelSet in enumerate(self.pixels):
            for pixel in pixelSet:
                pixel.setPlayer(self, (i+1)/len(self.pixels))

    def removeFromAllPixels(self):
		for pixelSet in self.pixels:
            for pixel in pixelSet:
                pixel.unsetPlayer()


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

def refillPowerups(count):
	# Find existing powerups
	existingCount = 0
	for line in lines:
		for pixel in line.pixels:
			if pixel.powerup:
				existingCount += 1

	availableLines = []
	for line in lines
		available = len(line.pixels) >= 3
        for pixel in line.pixels:
            available = available and pixel.player is None and pixel.powerup == False
        if available:
	        availableLines.append(line)
	random.shuffle(availableLines)

	for i in range(count - existingCount):
	    if i < len(availableLines):
	    	availableLines[i].pixels[random.randrange(1, len(availableLines[i].pixels)-1)].setPowerup()
	  
def resetGame():
	# Clear board and reset players
	for node in nodes:
		for pixel in node.pixels:
			pixel.reset()
	for line in lines:
		for pixel in line.pixels:
			pixel.reset()
	for player in players:
		player.reset()




def endGame():
	global gameRunning
	gameRunning = False

def startGame():
	global gameRunning
	gameRunning = True

##


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
players = [
    Player(nodes[0], 1, [255,0,0], moves[0]),
    Player(nodes[0], 2, [0,255,0], moves[1]),
    Player(nodes[0], 3, [0,0,255], moves[2]),
    Player(nodes[0], 4, [255,255,0], moves[3])
]
###


print("\n\n", [port.device for port in list_ports.comports()], "\n\n")
ser = serial.Serial('/dev/cu.wchusbserial1460', 115200)

time.sleep(2) # the serial connection resets the arduino, so give the program time to boot

pygame.init()
clock = pygame.time.Clock()

gameRunning = False

while True:
    clock.tick(30)

    if gameRunning:
        for player in players:
            player.update()

    	refillPowerups(4)

    	# Game over?
    	livingPlayers = list(filter(lambda player: player.alive, players))
    	if (livingPlayers <= 1):
    		endGame()
    else:
    	for player in players:
    		player.updateOutOfGame()

    	# Start game?
    	joinedPlayers = list(filter(lambda player: player.alive, players))
    	if len(joinedPlayers) > 0:
    		readyPlayers = list(filter(lambda player: player.ready, joinedPlayers))
    		if len(readyPlayers) == len(joinedPlayers) or len(joinedPlayers) == len(players):
    			startGame()



    # for event in pygame.event.get():
    #     if event.type == pygame.KEYDOWN:
    #         if event.key == pygame.K_TAB:
    #             player.advanceNodeExit()
    #         elif event.key == pygame.K_SPACE:
    #             player.goNodeExit()

    for strand in strands:
        pixelData = [pixel.getData() for pixel in getStrandPixels(strand)]
        print(pixelData)
        ser.write(bytes(pixelData))
        ser.flush()
        print(ser.readline())

