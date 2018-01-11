import pygame
import pygame.time
import random
import serial
from serial.tools import list_ports
import time
import sys
sys.path.insert(0, '/Projects/psmoveapi/build');
import psmove

pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((320, 240))
font = pygame.font.Font(None, 30)

##

class Node(object):

    def __init__(self):
        self.lines = []
        self.pixel = Pixel()
        self.pixels = [self.pixel]

    def addLine(self, line):
        self.lines.append(line)

    def pulse(self):
        self.pixel.pulse()

##

class Line(object):                        
   
    def __init__(self, pixelCount):
        self.node1 = None
        self.node2 = None
        self.line1 = None #continuing line from start
        self.line2 = None #continuing line from end
        self.pixels = []
        for i in range(pixelCount):
            self.pixels.append(Pixel())

    def isIndexAtConnection(self, index):
        if (index < 0):
            return self.node1 if self.node1 is not None else self.line1
        elif (index >= len(self.pixels)):
            return self.node2 if self.node2 is not None else self.line2
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

    def getDirectionFromLine(self, line):
        return 1 if line == self.line2 else -1

    def getFirstPixelIndexFromLine(self, line):
        return 0 if line == self.line2 else len(self.pixels)-1

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
        self.alpha = 1

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
        self.currentNode = self.startingNode
        self.currentNodeExitIndex = 0
        self.moveAccum = 0  #ticks up per frame, and movement happens when it's high enough
        self.moveMultiplier = 1
        self.movesBeforeMultiplierReset = 0 
        self.pixels = [self.startingNode.pixel] 
        self.length = 1
        self.alive = False
        self.ready = False # for starting the game

        #self.advanceToPixel(self.currentNode.pixel)
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
            self.moveAccum += 5 * self.moveMultiplier
            if (self.moveAccum >= 20):
                self.moveAccum -= 20
                self.currentLineIndex += self.currentLineDirection
                atConnection = self.currentLine.isIndexAtConnection(self.currentLineIndex)
                if atConnection is None:
                    self.advanceToPixel(self.currentLine.pixels[self.currentLineIndex])
                elif isinstance(atConnection, Line):
                    self.currentLine = atConnection
                    self.currentLineDirection = self.currentLine.getDirectionFromLine(self.currentNode)
                    self.currentLineIndex = self.currentLine.getFirstPixelIndexFromLine(self.currentNode)
                    self.advanceToPixel(self.currentLine.pixels[self.currentLineIndex])
                elif isinstance(atConnection, Node):
                    # Arrive at node
                    self.currentLine = None
                    self.currentNode = atConnection
                    self.currentNodeExitIndex = -1
                    self.moveAccum = 0
                    self.advanceToPixel(self.currentNode.pixel)

                if self.movesBeforeMultiplierReset > 0:
                    self.movesBeforeMultiplierReset -= 1
                    if self.movesBeforeMultiplierReset == 0:
                        self.moveMultiplier = 1

        # Staying still at a node
        if self.currentNode is not None:
            self.currentNode.pulse()

        self.move.update_leds()

    def updateOutOfGame(self):
        while self.move.poll():
            self.ready = self.move.get_trigger() > 0
            pressed, released = self.move.get_button_events()
            if (pressed & psmove.Btn_MOVE):
                self.alive = not self.alive
                if self.alive:
                    self.move.set_leds(self.colorValue[0], self.colorValue[1], self.colorValue[2])
                    self.advanceToPixel(self.currentNode.pixel)
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
            self.advanceToPixel(self.currentLine.pixels[self.currentLineIndex])

    def powerup(self):
        self.length += 2
        self.moveMultiplier = 2
        self.movesBeforeMultiplierReset = 10

    def kill(self):
        print("Dead")
        self.alive = False
        self.removeFromAllPixels()
        self.move.set_leds(0, 0, 0)
        self.move.update_leds()

    def collideWith(self, player):
        if self.pixels[-1] == player.pixels[-1]: 
            # head on collision
            if self.length >= player.length:
                player.kill()
            if self.length <= player.length:
                self.kill()
        else:
            self.kill()

    def advanceToPixel(self, newPixel):
        # Collision?
        if newPixel.player is not None and newPixel.player != self:
            self.collideWith(newPixel.player)
            if not self.alive:
                return;

        # Powerup?
        if newPixel.powerup:
            self.powerup()
            newPixel.unsetPowerup()

        self.pixels.append(newPixel);

        if (len(self.pixels) > self.length):
            self.pixels[0].unsetPlayer()
            self.pixels = self.pixels[1:]

        for i, pixel in enumerate(self.pixels):
            pixel.setPlayer(self, (i+1)/len(self.pixels))

    def removeFromAllPixels(self):
        for pixel in self.pixels:
            pixel.unsetPlayer()


##

def getStrandPixels(strand):
    pixels = []
    for thing in strand:
        pixels += thing.pixels
    return pixels


def connectStrand(things):
    for i in range(1, len(things)-1, 2):
        line1 = things[i-1]
        node = things[i]
        line2 = things[i+1]

        line1.node2 = node
        line2.node1 = node
        node.addLine(line1)
        node.addLine(line2)

    startingLine = things[0]
    endingLine = things[-1]

    startingLine.line1 = endingLine
    endingLine.line2 = startingLine

    return things

def refillPowerups(count):
    # Find existing powerups
    existingCount = 0
    for line in lines:
        for pixel in line.pixels:
            if pixel.powerup:
                existingCount += 1

    availableLines = []
    for line in lines:
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
        node.pixel.reset()
    for line in lines:
        for pixel in line.pixels:
            pixel.reset()
    for player in players:
        player.reset()

def endGame():
    global gameRunning
    gameRunning = False
    pygame.time.set_timer(USEREVENT_ENDGAME_COMPLETE, 2000)
    print("Game ended")

def startGame():
    global gameRunning
    gameRunning = True
    print("Game started")

##


### BOARD CONFIG
nodes = [Node(), Node(), Node(), Node(), Node(), Node(), Node(), Node(), Node(), Node(), Node(), Node(), Node()]
lines = [
    # 0
    Line(8), Line(8), Line(3), Line(11), Line(3), Line(11), Line(3), Line(6),
    # 8
    Line(3), Line(14), Line(20), Line(5), Line(8), Line(2), Line(2),
    # 15
    Line(3), Line(6), Line(8), Line(2), Line(21), Line(9), Line(2), Line(2),
    # 23
    Line(4), Line(3), Line(14), Line(3), Line(14), Line(7), Line(9)


]

strands = [
    connectStrand(list(reversed([lines[0], nodes[10], lines[1], nodes[5], lines[2], nodes[4], lines[3], nodes[1], lines[4], nodes[3], lines[5], nodes[9], lines[6], nodes[11], lines[7]]))),
    connectStrand(list(reversed([lines[8], nodes[11], lines[9], nodes[7], lines[10], nodes[12], lines[11], nodes[9], lines[12], nodes[8], lines[13], nodes[12], lines[14]]))),
    #connectStrand(list(reversed([lines[15], nodes[10], lines[16], nodes[6], lines[17], nodes[4], lines[18], nodes[3], lines[19], nodes[2], lines[20], nodes[7], lines[21], nodes[8], lines[22]]))),
    #connectStrand([lines[23], nodes[5], lines[24], nodes[2], lines[25], nodes[0], lines[26], nodes[1], lines[27], nodes[0], lines[28], nodes[6], lines[29]]),
]

startingNodes = [nodes[0], nodes[1]]
### 

### PSMOVE CONFIG
moves = [psmove.PSMove(x) for x in range(psmove.count_connected())]
###

### PLAYER CONFIG
players = [
    Player(nodes[0], 1, [255,0,0], moves[0]),
    Player(nodes[5], 2, [0,255,0], moves[1]),
    # Player(nodes[2], 3, [0,0,255], moves[2]),
    # Player(nodes[3], 4, [255,255,0], moves[3])
]
###

### SERIAL CONFIG
print("\n\n", [port.device for port in list_ports.comports()], "\n\n")
ser = serial.Serial('/dev/cu.usbmodem1441', 115200)
###

### MISC DECLARATIONS
USEREVENT_ENDGAME_COMPLETE = pygame.USEREVENT+1

gameRunning = False
###


### MAKE ROCKET GO

time.sleep(2) # the serial connection resets the arduino, so give the program time to boot

while True:
    screen.fill(pygame.Color('black'))
    screen.blit(font.render(str(int(clock.get_fps())), True, pygame.Color('white')), (50, 50))
    pygame.display.flip()

    clock.tick(30)

    if gameRunning:
        for player in players:
            player.update()

        refillPowerups(4)

        # Game over?
        livingPlayers = list(filter(lambda player: player.alive, players))
        if (len(livingPlayers) <= 1):
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

    for event in pygame.event.get():
        if event.type == USEREVENT_ENDGAME_COMPLETE:
            pygame.time.set_timer(USEREVENT_ENDGAME_COMPLETE, 0)
            resetGame()
        # if event.type == pygame.KEYDOWN:
        #     if event.key == pygame.K_TAB:
        #         player.advanceNodeExit()
        #     elif event.key == pygame.K_SPACE:
        #         player.goNodeExit()

    for strand in strands:
        pixelData = [pixel.getData() for pixel in getStrandPixels(strand)]
        ser.write(bytes(pixelData))
        ser.flush()

        #print(pixelData)
        #print(ser.readline())
        ser.readline()

