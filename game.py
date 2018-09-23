import pygame
import pygame.time
import random
import serial
import json
import time
import re
import sys
import math
import argparse
from fx import *
sys.path.insert(0, '/Projects/psmoveapi/build');
import psmove
try:
    from evdev import InputDevice, categorize, ecodes, list_devices
    gamepadsAvailable = True
except ImportError:
    gamepadsAvailable = False
try:
    from neopixel import *
    pixelsAvailable = True
except ImportError:
    pixelsAvailable = False

parser = argparse.ArgumentParser()
parser.add_argument('--noviz', action='store_const', const=True)
parser.add_argument('--full', action='store_const', const=True)
parser.add_argument('--enemies', action='store_const', const=True)
parser.add_argument('--nodecheck', action='store_const', const=True)
args = parser.parse_args()



pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.mixer.init()
pygame.init()
clock = pygame.time.Clock()
if args.full == True:
    screen = pygame.display.set_mode((1400, 900), pygame.FULLSCREEN|pygame.HWSURFACE)
else:
    screen = pygame.display.set_mode((1400, 900))
font = pygame.font.Font(None, 30)

##

class Node(object):

    def __init__(self, orientation):
        self.lines = []
        self.pixel = Pixel()
        self.pixels = [self.pixel]
        self.orientation = orientation

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
            line.pixels[line.getFirstPixelIndexFromNode(self)].unsetCapture()

    def hasNoPlayers(self):
        # also includes connected lines
        result = True
        for pixel in self.pixels:
            result = result and pixel.player is None
        for line in self.lines:
            result = result and line.hasNoPlayers()
        return result

    def getLineForOrderedIndex(self, index):
        line = None
        if self.orientation == 'up':
            if index == 0:
                line = self.lines[1]
            elif index == 1:
                line = self.lines[3]
            elif index == 2:
                line = self.lines[0]
            elif index == 3:
                line = self.lines[2]
        elif self.orientation == 'down':
            if index == 0:
                line = self.lines[0]
            elif index == 1:
                line = self.lines[3]
            elif index == 2:
                line = self.lines[1]
            elif index == 3:
                line = self.lines[2]
        return line

    def getLineForDirection(self, direction):
        line = None
        if self.orientation == 'up':
            if direction == 'up':
                line = self.lines[1]
            elif direction == 'right':
                line = self.lines[3]
            elif direction == 'down':
                line = self.lines[0]
            elif direction == 'left':
                line = self.lines[2]
        elif self.orientation == 'down':
            if direction == 'up':
                line = self.lines[0]
            elif direction == 'right':
                line = self.lines[3]
            elif direction == 'down':
                line = self.lines[1]
            elif direction == 'left':
                line = self.lines[2]
        return line     


##

class Line(object):                        
   
    def __init__(self, pixelCount, orientation):
        self.node1 = None
        self.node2 = None
        self.line1 = None #continuing line from start
        self.line2 = None #continuing line from end
        self.setPixelCount(pixelCount)
        self.orientation = orientation # the direction of +1 movement

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
        return 1 if line == self.line1 else -1

    def getFirstPixelIndexFromLine(self, line):
        return 0 if line == self.line1 else len(self.pixels)-1

    def clearCaptures(self):
        for pixel in self.pixels:
            pixel.unsetCapture()

    def hasNoPlayers(self):
        result = True
        for pixel in self.pixels:
            result = result and pixel.player is None
        return result

    def getDirectionForDirection(self, direction):
        if self.orientation == 'up':
            if direction == 'up':
                return 1
            elif direction == 'down':
                return -1
        if self.orientation == 'down':
            if direction == 'down':
                return 1
            elif direction == 'up':
                return -1
        if self.orientation == 'left':
            if direction == 'left':
                return 1
            elif direction == 'right':
                return -1
        if self.orientation == 'right':
            if direction == 'right':
                return 1
            elif direction == 'left':
                return -1
        return None
        


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
        self.playerCaptureTime = 0
        self.lastPlayer = None
        self.lastPlayerTime = None
        self.powerup = False
        self.ball = False
        self.sparkleSeed = random.random()

    def getData(self):
        color = self.getColor()
        alpha = self.getAlpha()
        return (color << 5) + round(alpha*31)

    def getColor(self):
        return self.color if self.colorOverride is None else self.colorOverride

    def getAlpha(self):
        return self.alpha if self.alphaOverride is None else self.alphaOverride

    def setPlayer(self, player):
        self.player = player
        self.color = player.color
        self.alpha = 2
        self.lastPlayer = player
        self.lastPlayerTime = pygame.time.get_ticks()
        if player.hasBall == True:
            self.playerCapture = player
            self.playerCaptureTime = pygame.time.get_ticks()

    def unsetPlayer(self, player):
        self.player = None
        self.color = 0

    def unsetCapture(self):
        self.playerCapture = None
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

    def setBall(self):
        self.ball = True
        self.setOverride(8, 1)

    def unsetBall(self):
        self.ball = False
        self.unsetOverride()

    def setOverride(self, color, alpha):
        self.colorOverride = color
        self.alphaOverride = alpha

    def unsetOverride(self):
        self.colorOverride = None
        self.alphaOverride = None

    def update(self):
        if self.lastPlayer is not None and self.player is None:
            self.color = self.lastPlayer.color
            self.alpha = 0.5 - min(1, (pygame.time.get_ticks() - self.lastPlayerTime)/150) * 0.5
            if self.alpha <= 0:
                self.lastPlayer = None
        elif self.playerCapture is not None and self.player is None:
            self.color = self.playerCapture.color
            self.alpha = 1 - min(1, (pygame.time.get_ticks() - self.playerCaptureTime)/750) * 0.95
            self.alpha += math.sin( (pygame.time.get_ticks() % (2000 + self.sparkleSeed*8000)) / (2000 + self.sparkleSeed*8000) * 6.28 ) * 0.05 + 0.05
        self.alpha = min(1, self.alpha)

    def pulse(self, speed):
        accum = (pygame.time.get_ticks() * speed * 0.4) % 200
        if accum > 100:
            accum = 200 - accum
        #self.alpha = max((0.1 + accum/100*0.9) ** 1, 0.2)
        self.alpha = 2 if accum > 40 else 0

##

class Player(object):

    def __init__(self, captures, startingNode, colorId, colorValue = None, gamepad = None, keys = None, nodeExitSound = None, pickupSound = None, winSound = None):
        self.captures = captures
        self.startingNode = startingNode
        self.color = colorId
        self.colorValue = colorValue
        self.gamepad = gamepad
        self.keys = keys
        self.nodeExitSound = nodeExitSound
        self.nodeExitSound.set_volume(0.3)
        self.pickupSound = pickupSound
        self.winSound = winSound
        self.reset()

    def reset(self):
        self.spawnAtNode(self.startingNode, False)
        self.ready = False # for starting the game

    def spawnAtNode(self, node, alive):
        self.currentLine = None
        self.currentLineIndex = 0
        self.currentLineDirection = 1
        self.currentNode = node
        self.currentNodeExitIndex = -1
        self.hasBall = False
        self.moveAccum = 0  #ticks up per frame, and movement happens when it's high enough
        self.rotateAccum = 0
        self.rotateStep = 0
        self.moveMultiplier = 1
        self.visitedNodes = [node]
        self.pixels = [node.pixel] 
        self.length = 1
        self.respawnAccum = 0
        self.alive = alive
        self.lastAccel = None
        self.lastMoveTime = 0

        self.advanceToPixel(self.currentNode.pixel)


    def update(self, events = [], delta = 33):
        if not self.alive:
            self.respawnAccum += 0.03 * delta
            if self.respawnAccum >= 100:
                if self.visitedNodes[-1].hasNoPlayers() == True:
                    self.visitedNodes[-1].clearCaptures()
                    self.spawnAtNode(self.visitedNodes[-1], True)
        
        if not self.alive:
            return

        # Controls
        if self.gamepad is not None:

            direction = None

            event = self.gamepad.read_one()
            while event is not None:
                if event.type == ecodes.EV_KEY and event.value == 1:
                    if event.code == ecodes.KEY_UP:
                        direction = 'up'
                    if event.code == ecodes.KEY_DOWN:
                        direction = 'down'
                    if event.code == ecodes.KEY_LEFT:
                        direction = 'left'
                    if event.code == ecodes.KEY_RIGHT:
                        direction = 'right'
                event = self.gamepad.read_one() # loop until we exhaust waiting events
            
            if direction is not None:
                self.goInDirection(direction)

        for event in events:
            if event.type == pygame.KEYDOWN and self.keys is not None:
                direction = None
                if event.key == self.keys[0]:
                    direction = 'up'
                if event.key == self.keys[1]:
                    direction = 'down'
                if event.key == self.keys[2]:
                    direction = 'left'
                if event.key == self.keys[3]:
                    direction = 'right'
                if direction is not None:
                    self.goInDirection(direction)

        # Rotation
        if self.currentNode is not None:
            ...
            # self.rotateAccum += 0.7
            # targetAccum = 3 + self.rotateStep * 0.8
            # if self.rotateAccum >= targetAccum:
            #     self.advanceNodeExit()
            #     self.rotateStep += 1
            #     self.rotateAccum = 0

        # Movement
        if self.currentLine is not None:
            if self.hasBall == False:
                self.moveAccum += 0.36 * delta * self.moveMultiplier 
            else:
                self.moveAccum += 0.36 * delta * self.moveMultiplier * 0.8

            targetAccum = 20

            while (self.moveAccum >= targetAccum):
                self.moveAccum -= targetAccum

                # determine next position
                nextLineIndex = self.currentLineIndex + self.currentLineDirection
                atConnection = self.currentLine.isIndexAtConnection(nextLineIndex)
                nextPixel = None
                nextLine = None
                nextNode = None
                nextLineDirection = None
                if atConnection is None:
                    nextPixel = self.currentLine.pixels[nextLineIndex]
                elif isinstance(atConnection, Line):
                    nextLine = atConnection
                    nextPixel = nextLine.pixels[nextLine.getFirstPixelIndexFromLine(self.currentLine)]
                    nextLineIndex = nextLine.getFirstPixelIndexFromLine(self.currentLine)
                    nextLineDirection = nextLine.getDirectionFromLine(self.currentLine)
                elif isinstance(atConnection, Node):
                    nextNode = atConnection
                    nextPixel = nextNode.pixel

                if self.advanceToPixel(nextPixel):
                    if atConnection is None:
                        self.currentLineIndex = nextLineIndex
                    elif isinstance(atConnection, Line):
                        self.currentLine = nextLine
                        self.currentLineIndex = nextLineIndex
                        self.currentLineDirection = nextLineDirection
                    elif isinstance(atConnection, Node):
                        self.currentLine = None
                        self.currentNode = nextNode
                        self.currentNodeExitIndex = -1
                        self.moveAccum = 0
                        self.rotateAccum = 0
                        self.rotateStep = 0
                        self.visitedNodes.append(self.currentNode)

        if self.currentNode is not None:
            self.pixels[0].pulse(2 if self.hasBall == True else 1)

    def updateOutOfGame(self, events):
        self.advanceToPixel(self.currentNode.pixel)
        self.alive = True
        if self.gamepad is not None:
            self.ready = ecodes.KEY_UP in self.gamepad.active_keys()
        elif self.keys is not None:
            self.ready = pygame.key.get_pressed()[self.keys[0]]
            
            # pressed, released = self.move.get_button_events()
            # if (pressed & psmove.Btn_MOVE):
            #     self.alive = not self.alive
            #     if self.alive:
            #         self.move.set_leds(self.colorValue[0], self.colorValue[1], self.colorValue[2])
            #         self.advanceToPixel(self.currentNode.pixel)
            #     else:
            #         self.move.set_leds(0, 0, 0)
            #         self.removeFromAllPixels()

    def goInDirection(self, direction):
        if self.currentNode is not None:
            self.goNodeExitWithLine(self.currentNode.getLineForDirection(direction))
        elif self.currentLine is not None:
            newLineDirection = self.currentLine.getDirectionForDirection(direction)
            if newLineDirection is not None:
                self.currentLineDirection = newLineDirection

    def advanceNodeExit(self):
        if self.currentNode:
            if self.currentNodeExitIndex is not None and self.currentNodeExitIndex >= 0:
                self.currentNode.getLineForOrderedIndex(self.currentNodeExitIndex).unsetPointer(self.color, self.currentNode)
            self.currentNodeExitIndex += 1
            self.currentNodeExitIndex %= len(self.currentNode.lines)
            self.currentNode.getLineForOrderedIndex(self.currentNodeExitIndex).setPointer(self.color, self.currentNode)

    def goNodeExit(self):
        if self.currentNode and self.currentNodeExitIndex >= 0:
            self.goNodeExitWithLine(self.currentNode.getLineForOrderedIndex(self.currentNodeExitIndex))

    def goNodeExitWithLine(self, line):
            self.currentLine = line
            self.currentLineDirection = self.currentLine.getDirectionFromNode(self.currentNode)
            self.currentLineIndex = self.currentLine.getFirstPixelIndexFromNode(self.currentNode)
            #self.currentNode.getLineForOrderedIndex(self.currentNodeExitIndex).unsetPointer(self.color, self.currentNode)
            self.currentNode = None
            self.moveAccum = 0
            self.advanceToPixel(self.currentLine.pixels[self.currentLineIndex])
            self.nodeExitSound.play()

    def powerup(self):
        #self.length += 2
        self.moveMultiplier += 0.3 * 1/self.moveMultiplier
        if self.moveMultiplier > 3:
            self.moveMultiplier = 3
        collectSound.play()

    def pickupBall(self):
        self.hasBall = True
        pickupSound.play()
        self.pickupSound.play()

    def kill(self):
        if self.hasBall == True:
            # Ball drop -- advance several pixels, keep going until we're clear of intersection and other things, and drop
            if self.currentNode is not None:
                dropLine = self.currentNode.lines[random.randrange(0, len(self.currentNode.lines))]
                dropLineIndex = dropLine.getFirstPixelIndexFromNode(self.currentNode)
            else:
                dropLine = self.currentLine
                dropLineIndex = self.currentLineIndex
            dropPixel = dropLine.pixels[dropLineIndex]
            steps = 0
            while steps < 10 or dropLineIndex == 0 or dropLineIndex == len(dropLine.pixels)-1 or dropPixel.powerup or dropPixel.ball or dropPixel.player:
                dropLineIndex = dropLineIndex + self.currentLineDirection
                atConnection = dropLine.isIndexAtConnection(dropLineIndex)
                if isinstance(atConnection, Line):
                    dropLineIndex = atConnection.getFirstPixelIndexFromLine(dropLine)
                    dropLine = atConnection
                elif isinstance(atConnection, Node):
                    exitIndex = (atConnection.lines.index(dropLine) + self.currentLineDirection) % len(atConnection.lines)
                    dropLine = atConnection.lines[exitIndex]
                    dropLineIndex = dropLine.getFirstPixelIndexFromNode(atConnection)
                steps += 1
                dropPixel = dropLine.pixels[dropLineIndex]

            dropPixel.setBall()


        self.alive = False
        self.hasBall = False
        self.respawnAccum = 0
        self.removeFromAllPixels()
        deathSound.play()

    def advanceToPixel(self, newPixel):
        # Collision?
        if newPixel.player is not None and newPixel.player != self:
            if self.hasBall:
                self.kill()
                return False
            elif newPixel.player.hasBall:
                newPixel.player.kill()
            else:
                self.currentLineDirection *= -1  # this works because we know this player is definitely moving
                return False

        self.pixels.append(newPixel)

        # Powerup?
        if newPixel.powerup:
            self.powerup()
            newPixel.unsetPowerup()

        if newPixel.ball and self.captures:
            self.pickupBall()
            newPixel.unsetBall()

        if (len(self.pixels) > self.length):
            self.pixels[0].unsetPlayer(self)
            self.pixels = self.pixels[1:]

        for i, pixel in enumerate(self.pixels):
            pixel.setPlayer(self)

        return True

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
    (255,0,170), #purple
    (255,0,0), #red
    (0,170,255), #cyan
    (226,255,0), #yellow
    (255,255,255), #white
    (0,255,0), #green
    (255,0,0) #unused
]

class Strand(object):

    def __init__(self, pixelCount, loop, orientation, pin, channel, vizLayout):
        self.pin = pin
        self.channel = channel
        if isinstance(orientation, str):
            self.things = [Line(pixelCount, orientation)]
        else:
            self.things = []
            for pair in orientation:
                line = Line(pair[0], pair[1])
                if len(self.things) > 0:
                    self.things[-1].line2 = line
                    line.line1 = self.things[-1]
                self.things += [line]
        self.vizPoints = vizLayout
        self.strip = None
        self.linkStrands = None

        if loop == True:
            self.things[0].line1 = self.things[-1]
            self.things[-1].line2 = self.things[0]

    def initPixels(self, linkStrands = None):
        self.linkStrands = linkStrands
        if pixelsAvailable and self.pin is not None:
            pixelCount = len(self.getPixels(True)) + 30
            self.strip = Adafruit_NeoPixel(pixelCount, self.pin, 800000, 10, False, 255, self.channel, ws.WS2812_STRIP)
            self.strip.begin()
            for i in range(pixelCount):
                self.strip.setPixelColor(i, Color(0,0,0))
            self.strip.show()

    def getPixels(self, withLinks):
        px = []
        for thing in self.things:
            px += thing.pixels

        if withLinks == True and self.linkStrands is not None:
            for strand in self.linkStrands:
                px += strand.getPixels(True)

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

        line1 = Line(pixelIndex - lineStart, line.orientation)
        if len(line1.pixels) > 0:
            line1.node2 = node
            if line.node1 is not None:
                line1.node1 = line.node1
                line.node1.replaceLine(line, line1)
            if line.line1 is not None:
                line1.line1 = line.line1
                line1.line1.line2 = line1
            node.addLine(line1)
            newThings = [line1] + newThings
            if (line1.node1 == line1.node2):
                print("line1 error", line1.node1)

        line2 = Line(len(line.pixels) - len(line1.pixels) - 1, line.orientation)
        if len(line2.pixels) > 0:
            line2.node1 = node
            if line.node2 is not None:
                line2.node2 = line.node2
                line.node2.replaceLine(line, line2)
            if line.line2 is not None:
                line2.line2 = line.line2
                line2.line2.line1 = line2
            node.addLine(line2) 
            newThings = newThings + [line2]
            if (line2.node1 == line2.node2):
                print("line1 error", line2.node1)

        self.things = self.things[:i] + newThings + self.things[i+1:]

    def writePixels(self):        
        if self.strip is not None:
            amps = 0
            pixels = 0
            for i, pixel in enumerate(self.getPixels(True)):

                if attractMode == True:
                    color = attractCycleFX.getPixel(i)
                    self.strip.setPixelColor(i, Color(color[0], color[1], color[2]))

                else:
                    color = pixel.getColor()
                    alpha = pixel.getAlpha() * 255
                    c = 0
                    if (color == 0):
                        c = Color(0, 0, 0)
                    elif (color == 1):
                        c = Color(round(alpha/2), 0, round(alpha*0.5/2))
                    elif (color == 2):
                        c = Color(round(alpha/2), 0, 0)
                    elif (color == 3):
                        c = Color(0, round(alpha/2), round(alpha/2))
                    elif (color == 4):
                        c = Color(round(alpha*0.8/2), round(alpha/2), 0)
                    elif (color == 5):
                        c = Color(round(alpha/3), round(alpha/3), round(alpha/3))
                    elif (color == 6):
                        c = Color(0, round(alpha), 0)
                    elif (color == 7):
                        c = Color(round(alpha), 0, 0)
                    elif (color == 8):
                        color = wheel(round(pygame.time.get_ticks()/2))
                        c = Color(color[0], color[1], color[2])

                    amps += ((c>>16)&255)/255*0.02 + ((c>>8)&255)/255*0.02 + (c&255)/255*0.02

                    if amps > 1.2:
                        print("AMP OVERAGE")
                        c = Color(0, 0, 0)

                    pixels += 1
                    if pixels == 60:
                        pixels = 0
                        amps = 0

                    self.strip.setPixelColor(i, c)

            self.strip.show()

    def renderVizLine(self, screen):
        for j in range(len(self.vizPoints)-1):
            start = self.vizPoints[j]
            end = self.vizPoints[j+1]
            pygame.draw.line(screen, (127, 127, 127), start[:2], end[:2], 20)  
                    
    def renderVizDots(self, screen):
        pixelIndex = 0
        for j in range(len(self.vizPoints)-1):
            start = self.vizPoints[j]
            end = self.vizPoints[j+1]
            vector = [end[0]-start[0], end[1]-start[1]]
            pixelEndIndex = pixelIndex + start[2]
            pixels = self.getPixels(False)[pixelIndex:pixelEndIndex]
            for i, pixel in enumerate(pixels):
                dist = (i+1) / (len(pixels)+1)
                if pixel.getColor() == 8:
                    color = wheel(round(pygame.time.get_ticks()/2))
                else:
                    color = VIZ_COLORS[pixel.getColor()]
                alpha = min(pixel.getAlpha() ** 0.3, 1)
                if attractMode == True:
                    color = attractCycleFX.getPixel(i)
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

def createNode(orientation, *args):
    node = Node(orientation)
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
            available = available and pixel.player is None and pixel.powerup == False and pixel.ball == False
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
    for pixel in getAllPixels():
        pixel.reset()
    for player in players:
        player.reset()
    pygame.time.set_timer(USEREVENT_STARTGAME_COMPLETE, 0)
    pygame.time.set_timer(USEREVENT_GAME_COMPLETE, 0)
    pygame.time.set_timer(USEREVENT_ENDGAME_START, 0)
    pygame.time.set_timer(USEREVENT_ENDGAME_COMPLETE, 0)
    pygame.time.set_timer(USEREVENT_WARNING_1, 0)
    pygame.time.set_timer(USEREVENT_WARNING_2, 0)
    pygame.time.set_timer(USEREVENT_BLINK, 0)
    pygame.time.set_timer(USEREVENT_BEAT, 0)

def endGame(winner):
    print("Game ended")
    global gameEnded
    global blinkColor
    gameEnded = True
    pygame.time.set_timer(USEREVENT_BEAT, 0)
    pygame.time.set_timer(USEREVENT_GAME_COMPLETE, 0)
    if winner is not None:
        blinkColor = winner.color
        winSound.play()
        winner.winSound.play()
    else:
        blinkColor = 0
        loseSound.play()
    pygame.time.set_timer(USEREVENT_BLINK, 400)
    pygame.time.set_timer(USEREVENT_ENDGAME_COMPLETE, 8000)

def startGame():
    print("Game started")
    global gameRunning
    global attractMode
    global attractModeStart
    gameRunning = True
    attractMode = False
    attractModeStart = False
    startSound.play()
    pygame.time.set_timer(USEREVENT_STARTGAME_COMPLETE, int(startSound.get_length()*1000))
    #startGamePart2()

def startGamePart2():
    global beatSpeed
    global powerupCount
    global strands
    beatSpeed = 700
    pygame.time.set_timer(USEREVENT_BEAT, beatSpeed) 
    pygame.time.set_timer(USEREVENT_GAME_COMPLETE, 120000)
    pygame.time.set_timer(USEREVENT_WARNING_1, 90000)
    pygame.time.set_timer(USEREVENT_WARNING_2, 110000)
    powerupCount = 6
    strands[0].getPixels(True)[random.choice([180, 420])].setBall()
    for enemy in enemies:
        enemy.alive = True

def warning1():
    warning1Sound.play()
    pygame.time.set_timer(USEREVENT_WARNING_1, 0)

def warning2():
    warning2Sound.play()
    pygame.time.set_timer(USEREVENT_WARNING_2, 0)

blinkCounter = 0
blinkColor = 0
def blink():
    global gameEnded
    if (gameEnded == False):
        return

    global blinkCounter
    blinkCounter += 1
    for i, pixel in enumerate(getAllPixels()):
        pixel.setOverride(0 if blinkCounter%2==i%2 else blinkColor, 0.5)

beatCounter = 0
beatSpeed = 0
def beat():
    global gameEnded
    if (gameEnded == True):
        return

    global beatCounter
    beatCounter += 1
    beatSounds[beatCounter % len(beatSounds)].play()

    global beatSpeed
    beatSpeed -= 2
    if beatSpeed < 200:
        beatSpeed = 200
    pygame.time.set_timer(USEREVENT_BEAT, beatSpeed) 


##


### BOARD CONFIG
layout = StrandLayoutManager()

strands = [ 
    Strand(480, True, [(120, 'up'), (120, 'down'), (120, 'up'), (120, 'down')], 18, 0, layout.data[0]), 
    Strand(120, True, 'right', 13, 1, layout.data[1]),
    Strand(120, True, 'right', None, None, layout.data[2]),
    Strand(120, True, 'right', None, None, layout.data[3]),
    Strand(120, True, 'right', None, None, layout.data[4]),
]
strands[0].initPixels()
strands[1].initPixels([strands[2], strands[3], strands[4]])

nodes = [
    createNode('up', strands[0], 23, strands[1], 93),
    createNode('up', strands[0], 47, strands[2], 99),
    createNode('up', strands[0], 71, strands[3], 114),
    createNode('up', strands[0], 95, strands[4], 110),

    createNode('down', strands[0], 144, strands[4], 1),
    createNode('down', strands[0], 167, strands[3], 15),
    createNode('down', strands[0], 191, strands[2], 12),
    createNode('down', strands[0], 216, strands[1], 18),

    createNode('up', strands[0], 263, strands[1], 32),
    createNode('up', strands[0], 287, strands[2], 38),
    createNode('up', strands[0], 311, strands[3], 53),
    createNode('up', strands[0], 335, strands[4], 49),

    createNode('down', strands[0], 384, strands[4], 62),
    createNode('down', strands[0], 408, strands[3], 77),
    createNode('down', strands[0], 432, strands[2], 74),
    createNode('down', strands[0], 457, strands[1], 80),
]   
### 

### GAMEPAD CONFIG

gamepads = []

def devicenum(device_path):
        digits = re.findall(r'\d+$', device_path)
        return [int(i) for i in digits]

if gamepadsAvailable:
    devices = sorted(list_devices('/dev/input'), key=devicenum)
    devices = devices = [InputDevice(path) for path in devices]
    for device in devices:
        if 'Shinecon' in device.name:
            gamepads += [device]

def getGamepad(name):
    for gamepad in gamepads:
        if name in gamepad.name:
            return gamepad
    return None

###

### PLAYER CONFIG
players = [
    Player(True, nodes[0], 1, [255,0,170], getGamepad('967A'), [pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d], pygame.mixer.Sound('sounds/270344_shoot-00.ogg'), pygame.mixer.Sound('sounds/vo_ball_pink.ogg'), pygame.mixer.Sound('sounds/vo_win_pink.ogg')),
    Player(True, nodes[3], 2, [255,0,0], getGamepad('8818'), None, pygame.mixer.Sound('sounds/270343_shoot-01.ogg'), pygame.mixer.Sound('sounds/vo_ball_red.ogg'), pygame.mixer.Sound('sounds/vo_win_red.ogg')),
    Player(True, nodes[8], 3, [0,200,255], getGamepad('8C91'), None, pygame.mixer.Sound('sounds/270336_shoot-02.ogg'), pygame.mixer.Sound('sounds/vo_ball_blue.ogg'), pygame.mixer.Sound('sounds/vo_win_blue.ogg')),
    Player(True, nodes[11], 4, [200,255,0], getGamepad('0ED9'), None, pygame.mixer.Sound('sounds/270335_shoot-03.ogg'), pygame.mixer.Sound('sounds/vo_ball_yellow.ogg'), pygame.mixer.Sound('sounds/vo_win_yellow.ogg')),
]

if (args.nodecheck == True):
    players += [
        Player(True, nodes[4], 4, [170,255,0], None, None, pygame.mixer.Sound('sounds/270335_shoot-03.ogg')),
        Player(True, nodes[5], 4, [170,255,0], None, None, pygame.mixer.Sound('sounds/270335_shoot-03.ogg')),
        Player(True, nodes[6], 4, [170,255,0], None, None, pygame.mixer.Sound('sounds/270335_shoot-03.ogg')),
        Player(True, nodes[7], 4, [170,255,0], None, None, pygame.mixer.Sound('sounds/270335_shoot-03.ogg')),
        Player(True, nodes[8], 4, [170,255,0], None, None, pygame.mixer.Sound('sounds/270335_shoot-03.ogg')),
        Player(True, nodes[9], 4, [170,255,0], None, None, pygame.mixer.Sound('sounds/270335_shoot-03.ogg')),
        Player(True, nodes[10], 4, [170,255,0], None, None, pygame.mixer.Sound('sounds/270335_shoot-03.ogg')),
        Player(True, nodes[11], 4, [170,255,0], None, None, pygame.mixer.Sound('sounds/270335_shoot-03.ogg')),
        Player(True, nodes[12], 4, [170,255,0], None, None, pygame.mixer.Sound('sounds/270335_shoot-03.ogg')),
        Player(True, nodes[13], 4, [170,255,0], None, None, pygame.mixer.Sound('sounds/270335_shoot-03.ogg')),
        Player(True, nodes[14], 4, [170,255,0], None, None, pygame.mixer.Sound('sounds/270335_shoot-03.ogg')),
        Player(True, nodes[15], 4, [170,255,0], None, None, pygame.mixer.Sound('sounds/270335_shoot-03.ogg')),
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
beatSounds[0].set_volume(0.2)
beatSounds[1].set_volume(0.2)
deathSound = pygame.mixer.Sound('sounds/270308_explosion-00.ogg')
deathSound.set_volume(0.7)
collectSound = pygame.mixer.Sound('sounds/270340_pickup-01.ogg')
collectSound.set_volume(0.3)
pickupSound = pygame.mixer.Sound('sounds/270341_pickup-04.ogg')
pickupSound.set_volume(0.7)
startSound = pygame.mixer.Sound('sounds/start.ogg')
winSound = pygame.mixer.Sound('sounds/270333_jingle-win-00.ogg')
loseSound = pygame.mixer.Sound('sounds/270329_jingle-lose-00.ogg')
warning1Sound = pygame.mixer.Sound('sounds/vo_30seconds.ogg')
warning2Sound = pygame.mixer.Sound('sounds/vo_10seconds.ogg')
attractVOs = [pygame.mixer.Sound('sounds/attract_vo_1.ogg'), pygame.mixer.Sound('sounds/attract_vo_2.ogg'), pygame.mixer.Sound('sounds/attract_vo_3.ogg'), pygame.mixer.Sound('sounds/attract_vo_4.ogg'), pygame.mixer.Sound('sounds/attract_vo_5.ogg'), pygame.mixer.Sound('sounds/attract_vo_6.ogg'), pygame.mixer.Sound('sounds/attract_vo_7.ogg'), pygame.mixer.Sound('sounds/attract_vo_8.ogg'), pygame.mixer.Sound('sounds/attract_vo_9.ogg'), pygame.mixer.Sound('sounds/attract_vo_10.ogg')]

### MISC DECLARATIONS
USEREVENT_STARTGAME_COMPLETE = pygame.USEREVENT+5
USEREVENT_GAME_COMPLETE = pygame.USEREVENT+6
USEREVENT_ENDGAME_START = pygame.USEREVENT+1
USEREVENT_ENDGAME_COMPLETE = pygame.USEREVENT+2
USEREVENT_WARNING_1 = pygame.USEREVENT+7
USEREVENT_WARNING_2 = pygame.USEREVENT+0
USEREVENT_BLINK = pygame.USEREVENT+3
USEREVENT_BEAT = pygame.USEREVENT+4

appRunning = True
gameRunning = False
gameEnded = False
powerupCount = 0

attractMode = False
attractModeStart = 0
attractCycleIndex = 0
attractCycleTime = 0
attractCycleFX = None
###


### MAKE ROCKET GO

while appRunning:
    if args.noviz != True: 
        screen.fill(pygame.Color('black'))
        for strand in strands:
           strand.renderVizLine(screen)
        for strand in strands:
           strand.renderVizDots(screen)
        screen.blit(font.render(str(int(clock.get_fps())), True, pygame.Color('white')), (5, 5))
        pygame.display.flip()
    
    pygame.display.set_caption(str(int(clock.get_fps())))   

    clock.tick(30)

    events = pygame.event.get()

    if gameRunning:
        if not gameEnded:
            for player in players:
                player.update(events, clock.get_time())

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
        readyPlayers = list(filter(lambda player: player.ready, players))
        if len(readyPlayers) >= 1:
            attractMode = False
            attractModeStart = False
            if len(readyPlayers) == len(players):
                startGame()
        elif len(readyPlayers) == 0 and attractModeStart == False:
            attractModeStart = pygame.time.get_ticks() + 10000

    for event in events:
        if event.type == USEREVENT_STARTGAME_COMPLETE:
            pygame.time.set_timer(USEREVENT_STARTGAME_COMPLETE, 0)
            startGamePart2()

        elif event.type == USEREVENT_GAME_COMPLETE:
            winner = None
            winnerCount = 0
            for player in players:
                playerCount = 0
                for px in getAllPixels():
                    if px.playerCapture == player:
                        playerCount += 1
                if playerCount > winnerCount:
                    winner = player
                    winnerCount = playerCount
            endGame(winner)

        elif event.type == USEREVENT_ENDGAME_COMPLETE:
            resetGame()

        elif event.type == USEREVENT_BLINK:
            blink()
        elif event.type == USEREVENT_BEAT:
            beat()
        elif event.type == USEREVENT_WARNING_1:
            warning1()
        elif event.type == USEREVENT_WARNING_2:
            warning2()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                appRunning = False
            if event.key == pygame.K_RETURN:
                if gameRunning == False:
                    startGame()
                # else:
                #     resetGame()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            layout.handleMouseDown(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP:
            layout.handleMouseUp()
        elif event.type == pygame.MOUSEMOTION:
            layout.handleMouseMove(event.pos)


    if attractMode == False and attractModeStart != False and attractModeStart < pygame.time.get_ticks():
        attractMode = True
    if attractMode == True:
        if pygame.time.get_ticks() > attractCycleTime:
            totalCycles = 3
            attractCycleIndex += 1
            attractCycleTime = pygame.time.get_ticks() + 10000
            if attractCycleIndex % totalCycles == 0:
                attractCycleFX = FXTrail(5, 5, 0.5, None)
            elif attractCycleIndex % totalCycles == 1:
                attractCycleFX = FXFunky()
            elif attractCycleIndex % totalCycles == 2:
                attractCycleFX = FXPulse(4, (85, 85, 85))
                vo = attractVOs[random.randrange(0, len(attractVOs))]
                vo.play()
                attractCycleTime = pygame.time.get_ticks() + vo.get_length() * 1000
                


    if attractCycleFX is not None:
        attractCycleFX.update()


    for strand in strands:
        strand.writePixels()

