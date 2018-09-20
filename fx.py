import random
import math

class FX(object):

	def __init__(self):
		self.frame = 0

	def update(self):
		self.frame += 1


class FXPulse(FX):

	def __init__(self, speed, color):
		FX.__init__(self)
		if color is None:
			color = randomColor()
		self.color = color
		self.speed = speed

	def update(self):
		FX.update(self)

	def getPixel(self, i):
		frame = (self.frame * self.speed) % 60
		if frame > 30:
			frame = 60 - frame
		alpha = frame/30
		return (round(self.color[0]*alpha), round(self.color[1]*alpha), round(self.color[2]*alpha))

class FXStartup(FX):

	def __init__(self):
		FX.__init__(self)
		self.stage = 0
		self.stageInc = 30
		self.nextStage = self.frame + self.stageInc
		self.pixels = [(0,0,0)] * 1000

	def update(self):
		FX.update(self)
		if self.frame == self.nextStage:
			self.stage += 1
			self.stageInc -= 1
			if self.stageInc == 0:
				self.stageInc = 1
			self.nextStage = self.frame + self.stageInc

			p = self.stage / 30
			white = min(self.stage / 90, 1)
			for i in range(len(self.pixels)):
				if random.random() < p:
					color = randomColor()
					r = round(color[0]*(1-white) + 84*white)
					g = round(color[1]*(1-white) + 84*white)
					b = round(color[2]*(1-white) + 84*white)
					self.pixels[i] = (r,g,b)
				else:
					self.pixels[i] = (0,0,0)

	def getPixel(self, i):
		return self.pixels[i]

class FXTrail(FX):

	def __init__(self, lengthOn, lengthOff, speed, color):
		FX.__init__(self)
		if color is None:
			color = randomColor()
		self.color = color
		self.lengthOn = lengthOn
		self.lengthOff = lengthOff
		self.speed = speed

	def update(self):
		FX.update(self)

	def getPixel(self, i):
		i += self.frame * self.speed
		i %= self.lengthOn + self.lengthOff
		if i < self.lengthOn:
			return self.color
		else:
			return (0,0,0)

class FXAmbient(FX):

	def __init__(self, speed):
		FX.__init__(self)
		self.speed = speed

	def update(self):
		FX.update(self)

	def getPixel(self, i):
		return wheel((i+(self.frame*self.speed)) % 256)

class FXFunky(FX):

	def getPixel(self, i):
		color = wheel((i+(self.frame)) % 256)
		alpha = math.sin((i+self.frame)*0.1) * 0.5 + 0.5
		color = (round(color[0]*alpha), round(color[1]*alpha), round(color[2]*alpha))
		return color


def randomColor():
	return wheel(random.randint(0, 255))

def wheel(pos):
	pos = pos % 256
	if pos < 85:
		return (pos * 3, 255 - pos * 3, 0)
	elif pos < 170:
		pos -= 85
		return (255 - pos * 3, 0, pos * 3)
	elif pos < 256:
		pos -= 170
		return (0, pos * 3, 255 - pos * 3)
