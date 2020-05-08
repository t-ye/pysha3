"""
Algorithms for computing discrete logarithms in integers modulo p, where p
is a prime.
"""

class DiscreteLogarithmProblem(object) :
	"""
	Struct-like class to describe a discrete logarithm problem. Given a prime p,
	g in Z/pZ*, and target t in subgroup of Z/pZ* generated by g, we wish to
	compute the discrete logarithm of t to base g, i.e. an x such that g**x =j
	t. Note that such an x exists if t is indeed in <g>, and is unique mod the
	multiplicative order of g.

	*THIS CLASS IS NOT USED IN THE ACTUAL DISCRETE LOGARITHM ALGORITHMS BELOW.*
	Using the class would require a lot of refactoring.
	"""

	def __init__(self, g, p, t, q = None, qfactors = None) :
		self.g = g
		self.p = p
		self.t = t
		self._q = None
		self._qfactors = None

	def check_wellposed(self) :
		pass

	def check_consistency(self) :
		pass

	def as_tuple(self, q=False, qfactors=False) :
		return (self.g, self.p, self.t)   + \
		       ( (self.q,) if q else () ) + \
			   ( (self.qfactors,) if qfactors else () )

	@property
	def q(self) :
		from ntheory import order
		if self._q == None :
			if self._qfactors != None :
				from utils import prod
				self._q = prod(r**e for r,e in self._qfactors.items())
			else :
				self._q = order(self.g, self.p)
		return self._q

	@property
	def qfactors(self) :
		if self._qfactors == None :
			from ntheory import factor
			self._qfactors = factor(self.q)
		return self._qfactors

	def __str__(self) :
		# https://stackoverflow.com/a/10660443/5708812
		fstr = (f'{type(self).__name__}(g={self.g}, p={self.p}, t={self.t}, '
			f'q={self._q or "TBD"}, qfactors={self._qfactors or "TBD"})')
		return fstr

	def __repr__(self) :
		return str(self)

DLP = DiscreteLogarithmProblem

def _dlog_check_params(g:int, p:int, t:int, q:int) :
	if (p-1) % q != 0 : raise ValueError('q needs to divide order of F_p*')
	# if g % p == 0 : raise ValueError('g == 0 mod p')
	if pow(g, q, p) != 1 : raise ValueError( 'g**q != 1: ' + str((g,p,q)) )


def dlog(g:int, p:int, t:int, q:int) :
	"""
	Compute first 0 <= x <= q-1 such that g^x = t mod p using a naive linear
	search.
	"""
	_dlog_check_params(g, p, t, q)

	t_ = 1
	for x in range(q) :
		if t_ == t :
			return x % (p-1)
		t_ *= g
		t_ %= p

	raise RuntimeError("Discrete logarithm not found: " + str((g,p,t,q)) )

def babygiantstep(g:int, p:int, t:int, q:int) :
	from itertools import islice
	from math import ceil
	from utils import isqrt

	_dlog_check_params(g, p, t, q)

	rootq = isqrt(q)

	# Dict (k,v) such that k = g**gpows{k].
	gpows = dict()

	# Compute and store g**(i*rootq) for i until (i+1)*rootq >= q. (We don't
	# need this i+1 because we have i=0=q mod q.) Thus we partition [0, q) into
	# intervals of size rootq.
	for i in range( int(ceil(q/rootq)) ) :
		gpows[pow(g, i*rootq, p)] = i*rootq

	# Find j such that t*g**j = g**(i*rootq) for some i, so that
	# t = g**(i*rootq-j) => Dlog_g(t) = i*rootq-j.
	for j in range(rootq) :
		t_gj = t*pow(g,j,p) % p
		if t_gj in gpows :
			return (gpows[t_gj] - j) % q # Reduce the exponent mod q = ord(g).

	raise RuntimeError("Discrete logarithm not found: " + str((g,p,t,q)) )


def pohlighellman(g:int, p:int, t:int, qfactors:list) :
	from ntheory import crt
	from utils import prod

	q = prod(qfactors)
	# Impose an order on factors.
	qfactors = list(qfactors)
	_dlog_check_params(g, p, t, q)

	# Raising g/t to q//qfactor projects g/t to the subgroup of <g> of order
	# qfactor.
	gprojs = [pow(g, q//qfactor, p) for qfactor in qfactors]
	tprojs = [pow(t, q//qfactor, p) for qfactor in qfactors]

	# Choose underlying discrete logarithm algorithm.
	DLOG = babygiantstep

	# Solve dlog_gproj(tproj) = x[i] = x mod qfactor.
	xs = [DLOG(gproj,p,tproj,qfactor) for (gproj, tproj, qfactor) in
		zip(gprojs, tprojs, qfactors)]

	# <g> is isomorphic to (Z/q, +).
	return crt(xs, qfactors)

def partial_pohlighellman(g:int, p:int, t:int, qfactors:list, B:int) :
	"""
	Solve the discrete logarithm problem for target t to base g, when both are
	projected down to the maximal subgroup of <g> which has B-smooth order.
	"""
	from utils import prod

	q = prod(qfactors)

	# Find the smooth part of q: z.
	# smoothfactors = {q_**e for q_,e in qfactors.items() if q_**e <= B}
	smoothfactors = [qfactor for qfactor in qfactors if qfactor<=B]
	z = prod(smoothfactors)


	# Do Pohlig-Hellman on the projection of g down to Z/zZ, so that we find a
	# relation V = x mod z. If x < z, then V = x mod n too; otherwise, x = Az +
	# V for some A to be determined.
	V = pohlighellman(pow(g, q//z, p) , p, pow(t, q//z, p), smoothfactors)

	# Hope V = x mod n.
	return V
