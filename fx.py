class FX(object):

	def __init__(self):
		self.frame = 0

	def update():
		self.frame += 1


class FXPulse(FX):

	def __init__(self, color):
		FX.__init__(self)
		self.color = color

	def update(self):
		FX.update(self)

	def getPixel(self, i):
		i = i % 60
		if i > 30:
			i = 60 - i
		alpha = i/30
		return (round(color[0]*alpha), round(color[1]*alpha), round(color[2]*alpha))


