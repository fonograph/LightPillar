import pygame
import pygame.time
import random
import serial
import json
import time
import sys
import math
import argparse
import fx
sys.path.insert(0, '/Projects/psmoveapi/build');
import psmove
try:
    from neopixel import *
    pixelsAvailable = True
except ImportError:
    pixelsAvailable = False

parser = argparse.ArgumentParser()
parser.add_argument('--rogue', '-r')
parser.add_argument('--noviz', action='store_const', const=True)
parser.add_argument('--enemies', action='store_const', const=True)
args = parser.parse_args()



pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init()
pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((1400, 900))# , pygame.FULLSCREEN|pygame.HWSURFACE)
font = pygame.font.Font(None, 30)

##

class Node(object):

    def __init__(self):
        self.lines = []
        self.pixel = Pixel()
        self.pixels = [self.pixel]

    def addLine(self, line):
        self.lines.append(line)

    def replaceLine(self, oldLine, newLine):
        self.lines = [line if (line != oldLine) else newLine for line in self.lines]

    def pulse(self):
        self.pixel.pulse()

    def clearCaptures(self):
        for pixel in self.pixels:
            pixel.unsetCapture()
        for line in self.lines:
            line.clearCaptures()

    def hasNoPlayers(self):
        # also includes connected lines
        result = True
        for pixel in self.pixels:
            result = result and pixel.player is None
        for line in self.lines:
            result = result and line.hasNoPlayers()
        return result

##

class Line(object):                        
   
    def __init__(self, pixelCount):
        self.node1 = None
        self.node2 = None
        self.line1 = None #continuing line from start
        self.line2 = None #continuing line from end
        self.setPixelCount(pixelCount)

    def setPixelCount(self, pixelCount):
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

    def clearCaptures(self):
        for pixel in self.pixels:
            pixel.unsetCapture()

    def hasNoPlayers(self):
        result = True
        for pixel in self.pixels:
            result = result and pixel.player is None
        return result


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
        self.playerCapture = None
        self.playerCapturePercent = 0
        self.powerup = False
        self.pulseTicker = 0;

    def getData(self):
        color = self.getColor()
        alpha = self.getAlpha()
        return (color << 5) + round(alpha*31)

    def getColor(self):
        return self.color if self.colorOverride is None else self.colorOverride

    def getAlpha(self):
        return self.alpha if self.alphaOverride is None else self.alphaOverride

    def setPlayer(self, player, alpha):
        self.player = player
        self.setOverride(player.color, alpha)
        if player.captures:
            self.playerCapture = player
            self.playerCapturePercent = 1

    def unsetPlayer(self, player):
        self.player = None
        self.unsetOverride()
        if player.captures:
            self.playerCapturePercent = 0.5

    def unsetCapture(self):
        self.playerCapture = None
        self.playerCapturePercent = 0
        self.color = 0

    def setLinePointer(self, color):
        self.setOverride(5, 1)

    def unsetLinePointer(self, color):
        self.unsetOverride()

    def setPowerup(self):
        self.powerup = True
        self.setOverride(6, 1)        

    def unsetPowerup(self):
        self.powerup = False
        self.unsetOverride()

    def setOverride(self, color, alpha):
        self.colorOverride = color
        self.alphaOverride = alpha

    def unsetOverride(self):
        self.colorOverride = None
        self.alphaOverride = None

    def update(self):
        # fade from capture
        minCapture = 0.05
        fadeSpeed = 0.001
        if self.playerCapture is not None and self.player is None:
            self.playerCapturePercent -= fadeSpeed;
            self.playerCapturePercent = max(self.playerCapturePercent, minCapture)
            self.color = self.playerCapture.color
            self.alpha = max(self.playerCapturePercent ** 2, 0.05)


    def pulse(self, accum):
        accum = accum % 200
        if accum > 100:
            accum = 200 - accum
        self.alpha = max((0.1 + accum/100*0.9) ** 2, 0.05)

##

class Player(object):

    def __init__(self, captures, startingNode, colorId, colorValue = None, move = None, key1 = None, key2 = None, nodeExitSound = None):
        self.captures = captures
        self.startingNode = startingNode
        self.color = colorId
        self.colorValue = colorValue
        self.move = move
        self.key1 = key1
        self.key2 = key2
        self.nodeExitSound = nodeExitSound
        self.reset()

    def reset(self):
        self.spawnAtNode(self.startingNode, False)
        self.ready = False # for starting the game
        if self.move is not None:
            self.move.set_leds(0, 0, 0)
            self.move.update_leds()

    def spawnAtNode(self, node, alive):
        self.currentLine = None
        self.currentLineIndex = 0
        self.currentLineDirection = 1
        self.currentNode = node
        self.currentNodeExitIndex = 0
        self.moveAccum = 0  #ticks up per frame, and movement happens when it's high enough
        self.moveMultiplier = 1
        self.movesBeforeMultiplierReset = 0
        self.visitedNodes = [node]
        self.pixels = [node.pixel] 
        self.length = 1
        self.respawnAccum = 0
        self.alive = alive
        self.pulseAccum = 0

        if self.alive and self.move is not None:
            self.move.set_leds(self.colorValue[0], self.colorValue[1], self.colorValue[2])
            self.move.update_leds()

        self.advanceToPixel(self.currentNode.pixel)


    def update(self, events = []):
        if not self.alive:
            self.respawnAccum += 1
            if self.respawnAccum >= 100:
                for node in reversed(self.visitedNodes):
                    if node.hasNoPlayers() == True:
                        self.spawnAtNode(node, True)
                        break
        
        if not self.alive:
            return

        # Controls
        if self.move is not None:
            while self.move.poll():
                pressed, released = self.move.get_button_events()
                if pressed & psmove.Btn_T:
                    self.goNodeExit()
                elif pressed & (psmove.Btn_TRIANGLE | psmove.Btn_CIRCLE | psmove.Btn_SQUARE | psmove.Btn_CROSS | psmove.Btn_MOVE):
                    self.advanceNodeExit()
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == self.key1:
                    self.goNodeExit()
                elif event.key == self.key2:
                    self.advanceNodeExit()

        # Movement
        if self.currentLine is not None:
            self.moveAccum += 3 * self.moveMultiplier

            # determine next position
            nextLineIndex = self.currentLineIndex + self.currentLineDirection
            atConnection = self.currentLine.isIndexAtConnection(nextLineIndex)
            if atConnection is None:
                nextPixel = self.currentLine.pixels[nextLineIndex]
            elif isinstance(atConnection, Line):
                nextLine = atConnection
                nextPixel = nextLine.pixels[nextLine.getFirstPixelIndexFromLine(self.currentLine)]
            elif isinstance(atConnection, Node):
                nextNode = atConnection
                nextPixel = nextNode.pixel

            targetAccum = 20
            if nextPixel.playerCapture is not None and nextPixel.playerCapture != self:
                targetAccum += nextPixel.playerCapturePercent * 40

            if (self.moveAccum >= targetAccum):
                self.moveAccum -= targetAccum

                if atConnection is None:
                    self.currentLineIndex = nextLineIndex
                    self.advanceToPixel(self.currentLine.pixels[self.currentLineIndex])
                elif isinstance(atConnection, Line):
                    lastLine = self.currentLine
                    self.currentLine = atConnection
                    self.currentLineDirection = self.currentLine.getDirectionFromLine(lastLine)
                    self.currentLineIndex = self.currentLine.getFirstPixelIndexFromLine(lastLine)
                    self.advanceToPixel(self.currentLine.pixels[self.currentLineIndex])
                elif isinstance(atConnection, Node):
                    # Arrive at node
                    self.currentLine = None
                    self.currentNode = atConnection
                    self.currentNodeExitIndex = -1
                    self.moveAccum = 0
                    self.advanceToPixel(self.currentNode.pixel)
                    if self.alive:
                        # if you died on the move don't count it as a visit
                        self.visitedNodes.append(self.currentNode)

                if self.movesBeforeMultiplierReset > 0:
                    self.movesBeforeMultiplierReset -= 1
                    if self.movesBeforeMultiplierReset == 0:
                        self.moveMultiplier = 1

        self.pulseAccum += 6
        self.pixels[0].pulse(self.pulseAccum)

        if self.move is not None:
            self.move.update_leds()

    def updateOutOfGame(self, events):
        self.advanceToPixel(self.currentNode.pixel)
        self.alive = True
        if self.move is not None:
            self.move.set_leds(self.colorValue[0], self.colorValue[1], self.colorValue[2])
            # while self.move.poll():
            #     self.ready = self.move.get_trigger() > 0
            #     pressed, released = self.move.get_button_events()
            #     if (pressed & psmove.Btn_MOVE):
            #         self.alive = not self.alive
            #         if self.alive:
            #             self.move.set_leds(self.colorValue[0], self.colorValue[1], self.colorValue[2])
            #             self.advanceToPixel(self.currentNode.pixel)
            #         else:
            #             self.move.set_leds(0, 0, 0)
            #             self.removeFromAllPixels()
            self.move.update_leds()
        # for event in events:
        #     if event.type == pygame.KEYDOWN:
        #         if event.key == self.key1:
        #             ...
        #         elif event.key == self.key2:
        #             ...

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
            self.nodeExitSound.play()

    def powerup(self):
        #self.length += 2
        self.moveMultiplier = 2
        self.movesBeforeMultiplierReset = 30
        collectSound.play()

        global beatSpeed
        beatSpeed -= 20
        if beatSpeed < 200:
            beatSpeed = 200
        pygame.time.set_timer(USEREVENT_BEAT, beatSpeed) 

    def kill(self):
        print("Dead")
        self.alive = False
        self.respawnAccum = 0
        self.removeFromAllPixels()
        if self.move is not None:
            self.move.set_leds(0, 0, 0)
            self.move.update_leds()
        deathSound.play()

    def collideWith(self, player):
        if self.moveMultiplier <= player.moveMultiplier:
            self.kill()
        if player.moveMultiplier <= self.moveMultiplier:
            player.kill()

        if self.currentLine is not None:
            self.currentLine.clearCaptures()
        else:
            self.currentNode.clearCaptures()

        # if self.pixels[-1] == player.pixels[-1]: 
        #     # head on collision
        #     if self.length >= player.length:
        #         player.kill()
        #     if self.length <= player.length:
        #         self.kill()
        # else:
        #     self.kill()

    def advanceToPixel(self, newPixel):
        self.pixels.append(newPixel);

        # Collision?
        if newPixel.player is not None and newPixel.player != self:
            self.collideWith(newPixel.player)
            if not self.alive:
                return;

        # Powerup?
        if newPixel.powerup:
            self.powerup()
            newPixel.unsetPowerup()

        if (len(self.pixels) > self.length):
            self.pixels[0].unsetPlayer(self)
            self.pixels = self.pixels[1:]

        for i, pixel in enumerate(self.pixels):
            pixel.setPlayer(self, (i+1)/len(self.pixels))

    def removeFromAllPixels(self):
        for pixel in self.pixels:
            pixel.unsetPlayer(self)

##

class Enemy(Player):

    def __init__(self, captures, startingNode, colorId):
        Player.__init__(self, captures, startingNode, colorId)
        self.nodeAccum = 0

    def update(self):
        if self.currentNode is not None:
            self.nodeAccum += 1
            if self.nodeAccum >= 30:
                self.nodeAccum = 0
                self.currentNodeExitIndex = random.randrange(0, len(self.currentNode.lines))
                self.goNodeExit()
        Player.update(self)
        

##

VIZ_COLORS = [
    (0,0,0),
    (255,0,170),
    (255,170,0),
    (0,170,255),
    (170,255,0),
    (255,255,255),
    (0,255,0),
    (255,0,0)
]

class Strand(object):

    def __init__(self, pixelCount, pin, channel, vizLayout):
        self.pin = pin
        self.channel = channel
        self.things = [Line(pixelCount)]
        self.vizPoints = vizLayout
        self.strip = None
        self.linkStrand = None

    def initPixels(self, linkStrand = None):
        self.linkStrand = linkStrand
        if pixelsAvailable and self.pin is not None:
            pixelCount = len(self.getPixels(True))
            self.strip = Adafruit_NeoPixel(pixelCount, self.pin, 800000, 10, False, 255, self.channel, ws.WS2812_STRIP)
            self.strip.begin()
            for i in range(pixelCount):
                self.strip.setPixelColor(i, Color(0,0,0))
            self.strip.show()

    def getPixels(self, withLinks):
        px = []
        for thing in self.things:
            px += thing.pixels

        if withLinks == True and self.linkStrand is not None:
            px += self.linkStrand.getPixels(True)

        return px

    def getLines(self):
        lines = []
        for thing in self.things:
            if isinstance(thing, Line):
                lines += [thing]
        return lines
        
    def insertNode(self, pixelIndex, node):
        line = None
        lineStart = 0
        lineEnd = 0
        i = 0
        while line is None:
            lineEnd = lineStart + len(self.things[i].pixels)
            if lineEnd > pixelIndex:
                line = self.things[i]
            else:
                lineStart = lineEnd
                i += 1

        newThings = [node]

        if (lineStart == pixelIndex and i > 0 and self.things[i-1] == node) or (lineEnd-1 == pixelIndex and i < len(self.things)-1 and self.things[i+1] == node):
            #inserting right beside the same node, just shorten the line
            line.setPixelCount(len(line.pixels)-1)
            self.things = self.things[:i] + [node] + self.things[i:]
            print('adjacent node')
            return

        line1 = Line(pixelIndex - lineStart)
        if len(line1.pixels) > 0:
            line1.node2 = node
            if line.node1 is not None:
                line1.node1 = line.node1
                line.node1.replaceLine(line, line1)
            node.addLine(line1)
            newThings = [line1] + newThings
            if (line1.node1 == line1.node2):
                print("line1 error", line1.node1)

        line2 = Line(len(line.pixels) - len(line1.pixels) - 1)
        if len(line2.pixels) > 0:
            line2.node1 = node
            if line.node2 is not None:
                line2.node2 = line.node2
                line.node2.replaceLine(line, line2)
            node.addLine(line2) 
            newThings = newThings + [line2]
            if (line2.node1 == line2.node2):
                print("line1 error", line2.node1)

        self.things = self.things[:i] + newThings + self.things[i+1:]

    def writePixels(self):        
        if self.strip is not None:
            for i, pixel in enumerate(self.getPixels(True)):

                if currentFX is not None:
                    color = currentFX.getPixel(i)
                    self.strip.setPixelColor(i, Color(color[0], color[1], color[2]))

                else:
                    color = pixel.getColor()
                    alpha = pixel.getAlpha() * 255
                    if (color == 0):
                      self.strip.setPixelColor(i, Color(0, 0, 0))
                    elif (color == 1):
                      self.strip.setPixelColor(i, Color(round(alpha/2), 0, round(alpha*0.5/2)))
                    elif (color == 2):
                      self.strip.setPixelColor(i, Color(round(alpha/2), round(alpha*0.3/2), 0))
                    elif (color == 3):
                      self.strip.setPixelColor(i, Color(0, round(alpha/2), round(alpha/2)))
                    elif (color == 4):
                      self.strip.setPixelColor(i, Color(round(alpha*0.8/2), round(alpha/2, 0)))
                    elif (color == 5):
                      self.strip.setPixelColor(i, Color(round(alpha/3), round(alpha/3), round(alpha/3)))
                    elif (color == 6):
                      self.strip.setPixelColor(i, Color(0, round(alpha), 0))
                    elif (color == 7):
                      self.strip.setPixelColor(i, Color(round(alpha), 0, 0))

            self.strip.show()
                    
    def renderViz(self, screen):
        pixelIndex = 0
        for j in range(len(self.vizPoints)-1):
            start = self.vizPoints[j]
            end = self.vizPoints[j+1]
            vector = [end[0]-start[0], end[1]-start[1]]
            pixelEndIndex = pixelIndex + start[2]
            pygame.draw.line(screen, (255, 255, 255), start[:2], end[:2], 20)                        
            pixels = self.getPixels(False)[pixelIndex:pixelEndIndex]
            for i, pixel in enumerate(pixels):
                dist = (i+1) / (len(pixels)+1)
                color = VIZ_COLORS[pixel.getColor()]
                alpha = pixel.getAlpha() ** 0.3
                if currentFX is not None:
                    color = currentFX.getPixel(i)
                else:
                    color = (color[0] * alpha, color[1] * alpha, color[2] * alpha)
                pygame.draw.circle(screen, color, [int(start[0] + dist*vector[0]), int(start[1] + dist*vector[1])], 5)
            pixelIndex = pixelEndIndex

        

##

class StrandLayoutManager(object):

    def __init__(self):
        self.data = json.load(open('layout.json'))
        self.activeStrand = None
        self.activeStrandPoint = None

    def save(self):
        data = []
        for strand in strands:
            data += [strand.vizPoints]
        json.dump(data, open('layout.json', 'w'), indent=2)

    def handleMouseDown(self, pos):
        for strand in strands:
            for i, point in enumerate(strand.vizPoints):
                if math.sqrt((pos[0]-point[0])**2 + (pos[1]-point[1])**2) < 15:
                    self.activeStrand = strand
                    self.activeStrandPoint = i                

    def handleMouseUp(self):
        self.activeStrand = None
        self.save()

    def handleMouseMove(self, pos):
        if self.activeStrand is not None:
            self.activeStrand.vizPoints[self.activeStrandPoint][0] = pos[0]            
            self.activeStrand.vizPoints[self.activeStrandPoint][1] = pos[1]            

## 

def getAllPixels():
    px = []
    for s in strands:
        px += s.getPixels(False)
    return px

def getAllLines():
    lines = []
    for s in strands:
        lines += s.getLines()
    return lines

def createNode(*args):
    node = Node()
    for i in range(0, len(args), 2):
        strand = args[i]
        position = args[i+1]
        strand.insertNode(position, node)
    return node
    

def refillPowerups(count):
    # Find existing powerups
    existingCount = 0
    for pixel in getAllPixels():
        if pixel.powerup:
            existingCount += 1

    availableLines = []
    for line in getAllLines():
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
    global gameRunning
    global gameEnded
    global powerupCount
    gameRunning = False
    gameEnded = False
    powerupCount = 0
    for node in nodes:
        node.pixel.reset()
    for line in getAllLines():
        for pixel in line.pixels:
            pixel.reset()
    for player in players:
        player.reset()

def endGame(winners):
    print("Game ended")
    global gameEnded
    global blinkColor
    gameEnded = True
    pygame.time.set_timer(USEREVENT_BEAT, 0)
    winSound.play()
    # if len(winners):
    #     blinkColor = winners[0].color
    #     winSound.play()
    # else:
    #     blinkColor = 0
    #     loseSound.play()
    # Let the last death linger for a second
    # pygame.time.set_timer(USEREVENT_ENDGAME_START, 600)

def endGamePart2():
    # Then flash for a bit
    pygame.time.set_timer(USEREVENT_BLINK, 400)
    pygame.time.set_timer(USEREVENT_ENDGAME_COMPLETE, 5000)

def startGame():
    print("Game started")
    global gameRunning
    gameRunning = True
    startGamePart2()
    startSound.play()
    #pygame.time.set_timer(USEREVENT_STARTGAME_COMPLETE, int(startSound.get_length()*1000))

def startGamePart2():
    global beatSpeed
    global powerupCount
    beatSpeed = 700
    pygame.time.set_timer(USEREVENT_BEAT, beatSpeed) 
    pygame.time.set_timer(USEREVENT_GAME_COMPLETE, 180000)
    powerupCount = 8   
    for enemy in enemies:
        enemy.alive = True


blinkCounter = 0
blinkColor = 0
def blink():
    global blinkCounter
    blinkCounter += 1
    for i, pixel in enumerate(getAllPixels()):
        pixel.setOverride(0 if blinkCounter%2==i%2 else blinkColor, 0.5)

beatCounter = 0
beatSpeed = 0
def beat():
    global beatCounter
    beatCounter += 1
    #beatSounds[beatCounter % len(beatSounds)].play()


##


### BOARD CONFIG
layout = StrandLayoutManager()

strands = [ 
    Strand(210, 18, 0, layout.data[0]), 
    Strand(210, None, None, layout.data[1]),
    Strand(210, 13, 1, layout.data[2]),
    Strand(210, None, None, layout.data[3]),
]
strands[0].initPixels(strands[1])
strands[2].initPixels(strands[2])


nodes = [
    createNode(strands[0], 0),
    createNode(strands[0], 29),
    createNode(strands[0], 59),
    createNode(strands[1], 0),
    createNode(strands[1], 29),
    createNode(strands[1], 59),
]   
### 

### PSMOVE CONFIG
moves = []
for x in range(4):
    if x < psmove.count_connected():
        moves += [psmove.PSMove(x)]
    else:
        moves += [None]

def getMove(serial):
    global moves
    for move in moves:
        if move is not None and move.get_serial() == serial:
            return move
    print('Could not find move ', serial)
    return None
###

### PLAYER CONFIG
players = [
    Player(True, nodes[4], 1, [255,0,170], getMove('00:06:f5:eb:4e:52'), pygame.K_1, pygame.K_q, pygame.mixer.Sound('sounds/270344_shoot-00.ogg')),
    Player(True, nodes[5], 2, [255,170,0], getMove('00:06:f7:16:fe:d1'), pygame.K_2, pygame.K_w, pygame.mixer.Sound('sounds/270343_shoot-01.ogg')),
    #Player(True, nodes[9], 3, [0,170,255], moves[2], pygame.K_3, pygame.K_e, pygame.mixer.Sound('sounds/270336_shoot-02.ogg')),
    #Player(True, nodes[12], 4, [170,255,0], moves[3], pygame.K_4, pygame.K_r, pygame.mixer.Sound('sounds/270335_shoot-03.ogg'))
]
###

### ENEMIES
enemies = []
if args.enemies == True:
    enemies = [
        Enemy(False, nodes[0], 7),
        Enemy(False, nodes[1], 7),
        Enemy(False, nodes[2], 7),
        Enemy(False, nodes[3], 7)
    ] 


### SOUNDS
beatSounds = [pygame.mixer.Sound('sounds/beat1.ogg'), pygame.mixer.Sound('sounds/beat2.ogg')]
deathSound = pygame.mixer.Sound('sounds/270308_explosion-00.ogg')
collectSound = pygame.mixer.Sound('sounds/270340_pickup-01.ogg')
startSound = pygame.mixer.Sound('sounds/270319_jingle-win-01.ogg')
winSound = pygame.mixer.Sound('sounds/270333_jingle-win-00.ogg')
loseSound = pygame.mixer.Sound('sounds/270329_jingle-lose-00.ogg')

### MISC DECLARATIONS
USEREVENT_STARTGAME_COMPLETE = pygame.USEREVENT+5
USEREVENT_GAME_COMPLETE = pygame.USEREVENT+6
USEREVENT_ENDGAME_START = pygame.USEREVENT+1
USEREVENT_ENDGAME_COMPLETE = pygame.USEREVENT+2
USEREVENT_BLINK = pygame.USEREVENT+3
USEREVENT_BEAT = pygame.USEREVENT+4

appRunning = True
gameRunning = False
gameEnded = False
powerupCount = 0
currentFX = None
###

### ROGUE CONTROLLER SETUP
rogueMove = getMove('00:06:f7:c9:6d:d4')
roguePlayer = None
if rogueMove is not None and args.rogue is not None:
    roguePlayer = players[int(args.rogue)-1]
    rogueMove.set_leds(roguePlayer.colorValue[0], roguePlayer.colorValue[1], roguePlayer.colorValue[2])
    rogueMove.update_leds()
###

### MAKE ROCKET GO

while appRunning:
    if args.noviz != True: 
        screen.fill(pygame.Color('black'))
        for strand in strands:
           strand.renderViz(screen)
        screen.blit(font.render(str(int(clock.get_fps())), True, pygame.Color('white')), (5, 5))
        pygame.display.flip()
    
    pygame.display.set_caption(str(int(clock.get_fps())))   

    clock.tick(30)

    events = pygame.event.get();

    if gameRunning:
        if not gameEnded:
            for player in players:
                player.update(events)

            for enemy in enemies:
                enemy.update()

            for pixel in getAllPixels():
                pixel.update()

            refillPowerups(powerupCount)

            # Game over?
            # livingPlayers = list(filter(lambda player: player.alive, players))
            # if (len(livingPlayers) <= 1):
            #     endGame(livingPlayers)
    else:
        for player in players:
            player.updateOutOfGame(events)

        # Start game?
        joinedPlayers = list(filter(lambda player: player.alive, players))
        if len(joinedPlayers) >= 2:
            readyPlayers = list(filter(lambda player: player.ready, joinedPlayers))
            if len(readyPlayers) == len(joinedPlayers): #or len(joinedPlayers) == len(players):
                startGame()

    for event in events:
        if event.type == USEREVENT_STARTGAME_COMPLETE:
            pygame.time.set_timer(USEREVENT_STARTGAME_COMPLETE, 0)
            startGamePart2()

        elif event.type == USEREVENT_GAME_COMPLETE:
            endGame([])

        elif event.type == USEREVENT_ENDGAME_START:
            pygame.time.set_timer(USEREVENT_ENDGAME_START, 0)
            endGamePart2()

        elif event.type == USEREVENT_ENDGAME_COMPLETE:
            pygame.time.set_timer(USEREVENT_ENDGAME_COMPLETE, 0)
            pygame.time.set_timer(USEREVENT_BLINK, 0)
            resetGame()

        elif event.type == USEREVENT_BLINK:
            blink()

        elif event.type == USEREVENT_BEAT:
            beat()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                appRunning = False
            if event.key == pygame.K_RETURN:
                if gameRunning == False:
                    startGame()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            layout.handleMouseDown(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP:
            layout.handleMouseUp()
        elif event.type == pygame.MOUSEMOTION:
            layout.handleMouseMove(event.pos)


    # ROGUE CONTROLLER
    if gameRunning and not gameEnded and roguePlayer is not None and rogueMove is not None:
        rogueMove.update_leds()
        while rogueMove.poll():
            pressed, released = rogueMove.get_button_events()
            if pressed & psmove.Btn_T:
                roguePlayer.goNodeExit()
            elif pressed & (psmove.Btn_TRIANGLE | psmove.Btn_CIRCLE | psmove.Btn_SQUARE | psmove.Btn_CROSS | psmove.Btn_MOVE):
                roguePlayer.advanceNodeExit()

    if currentFX is not None:
        currentFX.update()

    for strand in strands:
        strand.writePixels()

