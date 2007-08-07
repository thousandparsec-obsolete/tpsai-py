#! /usr/bin/python

from tp.netlib import Connection
from tp.netlib import failed, constants, objects
from tp.netlib.client import url2bits
from tp.client.cache import Cache

version = (0, 0, 1)

cache      = None
connection = None

import math
def dist(a, b):
	return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)

# FIXME: Duplicated from libtpclient-py
def apply(self, evt):
	if evt.what == "orders":
		if evt.action in ("remove", "change"):

			r = self.remove_orders(evt.id, evt.slot)
			if failed(r):
				raise IOError("Unable to remove the order %s from %s (%s)..." % (evt.slot, evt.id, r[1]))
		
		if evt.action in ("create", "change"):
			r = self.insert_order(evt.id, evt.slot, evt.change)
			if failed(r):
				raise IOError("Unable to insert the order %s (%r) from %s (%s)..." % (evt.slot, evt.change, evt.id, r[1]))

			if evt.slot == -1:
				evt.slot = len(cache.orders[evt.id])
				
			o = self.get_orders(evt.id, evt.slot)
			if failed(o):
				raise IOError("Unable to get the order %s from %s (%s)..." % (evt.slot, evt.id, o[1]))

			evt.change = o[0]
	else:
		raise ValueError("Can't deal with that yet!")

def OrderCreate(oid, slot, type, *args):
	order = objects.Order(0, oid, slot, type, 0, [], *args)
	event = cache.CacheDirtyEvent("orders", "create", oid, slot, order)
	connection.apply(event)
	cache.apply(event)

def OrderRemove(oid, slot):
	event = cache.CacheDirtyEvent("orders", "remove", oid, slot, None)
	connection.apply(event)
	cache.apply(event)

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
				if FLEET_TYPE == ref._subtype:
					s += "Fleet %i (" % ref.id
					for shipid, amount in ref.ships:
						s += "%s %s%s, " % (amount, cache.designs[shipid].name, ['', 's'][amount > 1])
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

# FIXME: These should be defined in a "profile" somewhere as they are all server specific...
PLANET_TYPE = 3
FLEET_TYPE  = 4


MOVE_ORDER       = None
BUILDFLEET_ORDER = None
COLONISE_ORDER   = None
MERGEFLEET_ORDER = None

FRIGATE_SPEED    = 200000000
BATTLESHIP_SPEED = 300000000

FRIGATE_BUILD    = 2
BATTLESHIP_BUILD = 6

FRIGATE_POWER    = 0.2
BATTLESHIP_POWER = 1.0

ASSEMBLE_DISTANCE = BATTLESHIP_SPEED * 4.0

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
			if asset._subtype == FLEET_TYPE:
				for shipid, num in asset.ships:
					# Scouts do nothing!
					if cache.designs[shipid].name == 'Scout':
						continue				
	
					# Frigates...
					if cache.designs[shipid].name == 'Frigate':
						power += FRIGATE_POWER*num
						continue

					if cache.designs[shipid].name == 'Battleship':
						# Battleships
						power += BATTLESHIP_POWER*num
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
			if threat._subtype == PLANET_TYPE:
				# Check if this is a homeworld
				if False:
					power += BATTLESHIP_POWER*5
				else:
					power += BATTLESHIP_POWER*2

			if threat._subtype == FLEET_TYPE:
				for shipid, num in threat.ships:
					# Scouts do nothing!
					if cache.designs[shipid].name == 'Scout':
						continue				
	
					# Frigates...
					if cache.designs[shipid].name == 'Frigate':
						power += FRIGATE_POWER*num
						continue

					# Battleships or unknown...
					power += BATTLESHIP_POWER*num

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


class Task(Reference):
	"""\
	A thing which needs to be done.
	"""
	class Fulfilment(object):
		"""\
		Fulfilment class contains a 'request' to Fullfil a certain task.
		"""
		def __init__(self, asset, soon, portion=100.0, direct=True, totally=True):
			## Error checking....
			if not isinstance(soon, float):
				try:
					soon = float(soon)
				except:
					raise TypeError("Fulfilment's 'soon' argument must be a float.")

			if not isinstance(portion, float):
				try:
					portion = float(portion)
				except:
					raise TypeError("Fulfilment's 'portion' argument must be a float.")

			if not isinstance(direct, bool):
				raise TypeError("Fulfilment's 'direct' argument must be a bool.")

			if not isinstance(totally, bool):
				raise TypeError("Fulfilment's 'totally' argument must be a bool.")

			if not isinstance(asset, Asset):
				raise TypeError("Fulfilment's 'asset' argument must be a Asset object.")

			self.soon    = soon
			self.asset   = asset
			self.portion = portion
			self.direct  = direct
			self.totally = totally

		def __str__(self):
			if self.direct:
				if self.totally:
					brackets = " [%s]"
				else:
					brackets = "![%s]"
			else:
				brackets = " {%s}"
			return brackets % ("%s in %.2f turns will complete %.2f%%" % (self.asset.__str__(True), self.soon, self.portion))
		__repr__ = __str__

		def __cmp__(self, other):
			if not isinstance(other, Task.Fulfilment):
				raise TypeError("Don't know how to compare these types?")
			return cmp((self.soon, self.portion), (other.soon, other.portion))

	def __init__(self, ref):
		if self.__class__ == Task:
			raise SyntaxError("Can not instanciate base Task class!")

		if not isinstance(ref, Reference):
			raise TypeError("Task's reference must be a Reference object.")

		## Actual method...
		Reference.__init__(self, [ref])
		self.assigned = []

	def __eq__(self, other):
		"""
		Too tasks are equal if they refer to the same thing.
		"""
		if not isinstance(other, Task):
			return False
		return self.ref == other.ref
	def __neq__(self, other):
		return not self.__eq__(other)
	def __cmp__(self, other):
		"""
		Tasks are compared by their portions if they are not equal.
		"""
		if self == other:
			return 0
		return cmp(self.portion(), other.portion())

	def ref(self):
		return self.refs[0]
	ref = property(ref)

	def type(self):
		return self.__class__
	type = property(type)

	def long(self):
		"""
		Long returns how long this task will take to complete in turns.
		"""
		if len(self.assigned) > 0:
			return self.assigned[-1].soon
		return float('inf')

	def portion(self):
		portion = 0
		totallyfulfil = False

		for fulfilment in self.assigned:
			portion += fulfilment.portion
			if fulfilment.totally:
				totallyfulfil = True

		if not totallyfulfil:
			portion = min(portion, 99)

		return portion

	def assign(self, fulfilment):
		"""
		Assign an asset to this task.

		Soon is how soon this asset will complete it's "portion" of the task.

		Adding a new asset which would take the number of assets working on
		the task above 100% will cause the method to return a list of
		assets which are no longer needed.
		"""
		## Error checking....
		if not isinstance(fulfilment, Task.Fulfilment):
			raise TypeError("Assign's argument must be a Fulfilment object.")
		if self == fulfilment.asset:
			raise TypeError("Can not be assigned to oneself...")

		## Actual method...
		self.assigned.append(fulfilment)
		self.assigned.sort()

		portion = 0
		totallyfulfil = False
		
		for i, fulfilment in enumerate(self.assigned):
			portion += fulfilment.portion
			if fulfilment.totally:
				totallyfulfil = True

			if portion >= 100 and totallyfulfil:
				break

		i += 1

		leftover = self.assigned[i:]
		del self.assigned[i:]
		return [fulfilment.asset for fulfilment in leftover]

	def __str__(self, short=False):
		if short:
			if len(self.assigned) > 0:
				return "<Task %s - %s (%.0f%%)>" % (self.name, self.ref, self.portion())
			else:
				return "<Task %s - %s (unassigned)>" % (self.name, self.ref)

		if len(self.assigned) > 0:
			s = '['
			for fulfilment in self.assigned:
				s+= "\n\t%s, " % fulfilment
			s = s[:-2] +"]"
			return "<Task %s - %s ((%.0f%%) assigned to %s)>" % (self.name, self.ref, self.portion(), s)
		else:
			return "<Task %s - %s (unassigned)>" % (self.name, self.ref)
	__repr__ = __str__

	def flagship(self):
		"""
		Returns the flagship for the fleet which will fulfil the task.
		Also returns if this flagship has yet to be built.

		(asset, built?)
		"""
		distances = {}
		for fulfilment in self.assigned:
			distances[dist(fulfilment.asset.ref.pos, self.ref.pos[0])] = (fulfilment.asset, fulfilment.direct)

		keys = distances.keys()
		keys.sort()

		# Don't want to assemble too close to the target!
		# FIXME: If we are orbiting a planet, probably safe to use this ship...
		while len(keys) > 1:
			if keys[0] > ASSEMBLE_DISTANCE:
				break
			keys.pop(0)

		return distances[keys[0]]

	def issue(self):
		"""\
		Issue the correct orders to the assigned assets..
		"""
		used_assets = []

		# First job is to collect all the assets together
		if len(self.assigned) > 1 or self.portion() < 100:
			# Find the flagship
			flagship, flagbuilt = self.flagship()
			print "Flagship is", flagship, "assembling at", flagship.pos[0]
			print

			for fulfilment in self.assigned:
				used_assets.append(fulfilment.asset)

				print "Orders for", fulfilment.asset.__str__(True)
				slot=0
				if fulfilment.direct:
					slot += OrderAdd_Move(fulfilment.asset, flagship.pos[0], slot)
					if flagbuilt:
						slot += OrderAdd_Merge(fulfilment.asset, flagship, slot)
				else:
					slot += OrderAdd_Build(fulfilment.asset, self, slot)
				OrderAdd_Nothing(fulfilment.asset, slot)
				OrderPrint(fulfilment.asset)

		return used_assets

	def requirements(self, asset):
		"""\
		Issues the correct orders to fufill this task..
		"""
		raise SyntaxError("This task doesn't impliment the requirements order!")

class TaskDestroy(Task):
	name = 'Destroy '

	def issue(self):
		"""\
		Issue the correct orders to the assigned assets..
		"""
		# First job is to collect all the assets together
		used_assets = Task.issue(self)

		# Second job is to move the asset to the target's position
		if len(self.assigned) == 1 and self.portion() >= 100:
			fulfilment = self.assigned[0]

			used_assets.append(fulfilment.asset)

			print "Orders for", fulfilment.asset.__str__(True)
			slot = 0
			if fulfilment.direct:
				# FIXME: Should actually try an intercept the target!
				slot += OrderAdd_Move(fulfilment.asset, self.ref.pos[0], slot)
			else:
				slot += OrderAdd_Build(fulfilment.asset, self, slot)
			OrderAdd_Nothing(fulfilment.asset, slot)
			OrderPrint(fulfilment.asset)

		return used_assets

class TaskColonise(Task):
	name = 'Colonise'

	def issue(self):
		# First job is to collect all the assets together
		used_assets = Task.issue(self)

		# Second job is to move the asset to the target's position
		# Third  job is to colonise the target
		if len(self.assigned) == 1 and self.portion() >= 100:
			fulfilment = self.assigned[0]

			used_assets.append(fulfilment.asset)

			print "Orders for", fulfilment.asset.__str__(True)
			slot = 0
			if fulfilment.direct:
				slot += OrderAdd_Move(fulfilment.asset, self.ref.pos[0], slot)
				slot += OrderAdd_Colonise(fulfilment.asset, self.ref, slot)
			else:
				slot += OrderAdd_Build(fulfilment.asset, self, slot)
			OrderAdd_Nothing(fulfilment.asset, slot)
			OrderPrint(fulfilment.asset)

		return used_assets

class TaskTakeOver(TaskColonise):
	name = 'TakeOver'

	def issue(self):
		# First job is to collect all the assets together
		used_assets = Task.issue(self)

		# Second job is to move the asset to the target's position
		# Third  job is to colonise the target
		if len(self.assigned) == 1 and self.portion() >= 100:
			fulfilment = self.assigned[0]

			used_assets.append(fulfilment.asset)

			print "Orders for", fulfilment.asset.__str__(True)
			slot=0
			if fulfilment.direct:
				slot += OrderAdd_Move(fulfilment.asset, self.ref.pos[0], slot)
				slot += OrderAdd_Colonise(fulfilment.asset, self.ref, slot)
			else:
				slot += OrderAdd_Build(fulfilment.asset, self, slot)
			OrderAdd_Nothing(fulfilment.asset, slot)
			OrderPrint(fulfilment.asset)

		return used_assets

# FIXME: Better way to do this...
Task.DESTROY  = TaskDestroy
Task.COLONISE = TaskColonise
Task.TAKEOVER = TaskTakeOver
Task.types = (Task.DESTROY, Task.COLONISE, Task.TAKEOVER)

def OrderPrint(asset):
	"""\
	Print out the order completion time...
	"""
	for i, order in enumerate(cache.orders[asset.ref.id]):
		print "Order %i will complete in %.2f turns (%r)" % (i, order.turns, order)
	print

def OrderAdd_Nothing(asset, slot):
	"""\
	This function removed any remaining orders which might still exist!
	"""
	oid = asset.ref.id
	while True:
		# Check if the asset already has this order
		if asset.ref.order_number > slot:
			order = cache.orders[oid][slot]
			
			print "Extra order    - Remove this %r extra order" % (order,)
			OrderRemove(oid, slot)
		else:
			break
	return True


def OrderAdd_Move(asset, pos, slot):
	"""\
	This function issues orders for the asset to move to the given position.

	It won't add any orders if the asset is at the given position.
	"""
	if asset.ref.pos == pos:
		print "Move Order     - Object already at destination!"
		return False

	# FIXME: Check that asset can move!

	oid = asset.ref.id
	while True:
		# Check if the asset already has this order
		if asset.ref.order_number > slot:
			order = cache.orders[oid][slot]
			
			# Remove the order if it isn't a move order
			if order.subtype != MOVE_ORDER:
				print "Move order     - Current order (%r) wasn't a move order!" % order
				OrderRemove(oid, slot)
				continue

			# Remove the order if it isn't a move order to the correct location
			if order.pos != pos:
				print "Move order     - Current order (%r) was too wrong destination!" % order
				OrderRemove(oid, slot)
				continue

			# Order is correct
			print "Move order     - Already had correct move order."
			break
		else:
			print "Move order     - Issuing new order to move too %s" % (pos,)
			# We need to issue a move order instead.
			OrderCreate(oid, -1, MOVE_ORDER, pos)
			break
	return True

def OrderAdd_Colonise(asset, targets, slot):
	# Find the planet which we want to colonise
	target = None
	for ref in targets.refs:
		if ref._subtype == PLANET_TYPE:
			target = ref
			break
	if target is None:
		raise TypeError("Trying to colonise something which isn't a planet!")

	oid = asset.ref.id
	while True:
		if asset.ref.order_number > slot:
			order = cache.orders[oid][slot]

			# Remove the order if it isn't a colonise order
			if order.subtype != COLONISE_ORDER:
				print "Colonise order - Current order (%r) wasn't a colonise order!" % order
				OrderRemove(oid, slot)
				continue

			# Order is correct
			print "Colonise order - Already had correct colonise order (%r)." % (target,)
			break
		else:
			print "Colonise order - Issuing new order colonise %r" % (target,)
			# We need to issue a move order instead.
			OrderCreate(oid, -1, COLONISE_ORDER, target.id)
			break

	return True

def OrderAdd_Merge(asset, target, slot):
	# FIXME: Check that asset and target are both Fleets!
	if asset.ref.id == target.ref.id:
		return False

	oid = asset.ref.id
	while True:
		if asset.ref.order_number > slot:
			order = cache.orders[oid][slot]

			# Remove the order if it isn't a move order
			if order.subtype != MERGEFLEET_ORDER:
				print "Merge order    - Current order (%r) wasn't a Merge order!" % order
				OrderRemove(oid, slot)
				continue

			# Order is correct
			print "Merge order    - Object already had correct MergeFleet order."
			break
		else:
			print "Merge order    - Issuing orders to merge with %r" % (target.ref,)
			# We need to issue a move order instead.
			OrderCreate(oid, -1, MERGEFLEET_ORDER)
			break

	return True

def OrderAdd_Build(asset, task, slot):
	oid = asset.ref.id

	# Do a "probe" to work out the types
	OrderCreate(oid, 0, BUILDFLEET_ORDER, [], [], 0, "")
	result = cache.orders[oid][0]
	OrderRemove(oid, 0)
	ships = {}
	for id, name, max in result.ships[0]:
		ships[name] = id

	# Add the new build order
	tobuild = []
	if task.type in (Task.COLONISE, Task.TAKEOVER):
		# If we are referencing a colonise, better build a frigate
		print "Issuing orders to build a frigate"
		tobuild.append((ships['Frigate'],1))

	if task.type in (Task.DESTROY, Task.TAKEOVER):
		# Better build a battleship
		print "Issuing orders to build a battleship"
		tobuild.append((ships['Battleship'],1))

	while True:
		if asset.ref.order_number > slot:
			order = cache.orders[oid][slot]

			# Remove the order if it isn't a colonise order
			if order.subtype != BUILDFLEET_ORDER:
				print "Build order    - Current order (%r) wasn't a build order!" % order
				OrderRemove(oid, slot)
				continue

			if order.ships[1] != tobuild:
				print "Build order    - Current order (%r) wasn't building the correct stuff!" % order
				OrderRemove(oid, slot)
				continue

			# Order is correct
			print "Build order    - Already had correct build order."
			break
		else:
			print "Build order    - Issuing new order build."
			# We need to issue a move order instead.
			OrderCreate(oid, 0, BUILDFLEET_ORDER, [], tobuild, 0, "A robot army!")
			break

	return True
