#! /usr/bin/python

from tp.netlib import Connection
from tp.netlib import failed, constants, objects
from tp.netlib.client import url2bits
from tp.client.cache import Cache, apply

import server

version = (0, 0, 1)

import math
def dist(a, b):
	return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)

def OrderCreate(oid, type, *args):
	return objects.Order(0, oid, -1, type, 0, [], *args)

class LayeredIn(list):
	def __contains__(self, value):
		if list.__contains__(self, value):
			return True
		for l in self:
			if isinstance(l, (tuple, list)) and value in l:
				return True
		return False

class Reference(object):
	"""\
	Something which refers to something else.
	"""
	def __init__(self, refs):
		if not isinstance(refs, list):
			raise TypeError('Reference must referance a list!')

		self.refs = refs

	def __str__(self, short=False):
		s = ""
		for ref in self.refs:
			if isinstance(ref, Reference):
				s += str(ref)
			else:
				if server.FLEET_TYPE == ref._subtype:
					s += "Fleet %i (" % ref.id
					for shipid, amount in ref.ships:
						s += "%s %s%s, " % (amount, server.cache.designs[shipid].name, ['', 's'][amount > 1])
					s = s[:-2] + ")"
				else:
					s += repr(ref)[1:-1]
			s += ", "	

		s = s[:-2]
		if short:
			return s
		return "<%s refs=%s>" % (self.__class__.__name__, s)
	__repr__ = __str__

	def __getattr__(self, value):
		"""\
		This proxy class lets you use the following idiom,

		Say you create a reference which points to a list of objects,
		a = Reference([obj1, obj2])

		If both either obj1 or obj2 has an attribue "subtype" with value COLONISE,
		you can do:

		>>> class obj:
		>>> 	pass
		>>>
		>>> obj1 = obj()
		>>> obj2 = obj()
		>>> obj1.subtype = COLONISE
		>>> obj1.orders = [COLONISE, 19]
		>>> obj1.pos    = [10, 10, 10]
		>>> obj2.subtype = OTHER
		>>> obj2.orders = [78, OTHER]
		>>> obj2.pos    = [10, 10, 10]
		>>> r = Reference([obj1, obj2])

		>>> COLONISE in r.subtype
		True

		>>> 22 in r.subtype
		False

		>>> 78 in r.other
		True

		>>> 100 in r.other
		False

		>>> print obj2.pos
		[10, 10, 10]
		"""
		if value in ('refs', 'ref'):
			raise SyntaxError('__getattr__ got %s, this should not happen!' % value)

		r = LayeredIn()
		for ref in self.refs:
			if not hasattr(ref, value):
				raise TypeError("One of the references (%r) does not have that attribute (%s)!" % (ref, value))

			v = getattr(ref, value)
			if not v in r:
				r.append(v)

		return r

MARGIN = 5

class Asset(Reference):
	"""\
	An asset is anything which has value to the computer.
	"""

	def power(self):
		"""\
		Returns how powerful an object is.
		"""
		# A Planet is always has no power
		# A fleet is as powerful as the sum of it parts

		power = 0

		for asset in self.refs:
			if asset._subtype == server.FLEET_TYPE:
				for shipid, num in asset.ships:
					# Scouts do nothing!
					if server.cache.designs[shipid].name == 'Scout':
						continue				
	
					# Frigates...
					if server.cache.designs[shipid].name == 'Frigate':
						power += server.FRIGATE_POWER*num
						continue

					if server.cache.designs[shipid].name == 'Battleship':
						# Battleships
						power += server.BATTLESHIP_POWER*num
						continue

					print "WARNING! Unknown ship type!"

		return power

	def ref(self):
		return self.refs[0]
	ref = property(ref)

	def __eq__(self, other):
		if not isinstance(other, Asset):
			return False
		return self.ref.id == other.ref.id

	def __neq__(self, other):
		return not self.__eq__(other)

class Threat(Reference):
	"""\
	A threat is anything which could possibly hurt the computer.
	"""

	def threat(self):
		"""\
		This function returns two values.

		The first value is how threatening the object is in "absolute" terms.
		The second value is how soon this threat must be delt with.
		"""
		# Planets are more threatening but can be dealt with over a longer period of time
		# Ships are less threatening but are more urgent
		#	Unarmed ships are ignored
		#   Big groups of ships are more important
		# Threats which are closer to assets are more threatening
		pass

	def power(self):
		"""\
		Returns how powerful an object is.
		"""
		power = 0

		for threat in self.refs:
			if threat._subtype == server.PLANET_TYPE:
				# Check if this is a homeworld
				if False:
					power += server.BATTLESHIP_POWER*5
				else:
					power += server.BATTLESHIP_POWER*2

			if threat._subtype == server.FLEET_TYPE:
				for shipid, num in threat.ships:
					# Scouts do nothing!
					if server.cache.designs[shipid].name == 'Scout':
						continue				
	
					# Frigates...
					if server.cache.designs[shipid].name == 'Frigate':
						power += server.FRIGATE_POWER*num
						continue

					# Battleships or unknown...
					power += server.BATTLESHIP_POWER*num

		return power

	def __eq__(self, other):
		if not isinstance(other, Threat):
			return False
		return [ref.id for ref in self.refs] == [ref.id for ref in other.refs]

	def __neq__(self, other):
		return not self.__eq__(other)


class Neutral(Asset, Threat):
	"""\
	A Neutral object is anything which could possibly be an asset or a threat to the computer.
	"""
	def ref(self):
		return self.refs[0]
	ref = property(ref)

	def __eq__(self, other):
		if not isinstance(other, Neutral):
			return False
		return self.ref.id == other.ref.id

	def __neq__(self, other):
		return not self.__eq__(other)


