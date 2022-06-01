import random
import util
from util import log
from const import *

_cached_textdata = {}

def ensure_cached(dict_path):
	if _cached_textdata.get(dict_path.name):
		return
	
	with dict_path.open("r", encoding="utf-8") as fhandle:
		lines = fhandle.readlines()
	_cached_textdata[dict_path.name] = [s.strip() for s in lines]

def get_moniker(plural=False):
	is_doubled = util.chance(0.05)
	
	gr, adj_ending = _get_base_gr(plural=plural)
	adjectives = get_adjectives(ending=adj_ending)
	
	if is_doubled:
		suffix_gr, _ = _get_base_gr(plural=plural)
		gr = f"{gr}-{suffix_gr}"
	
	return f"{adjectives} {gr}"

def get_adjectives(ending=None, max_count=3):
	ensure_cached(TEXT_ADJECTIVES_DICT)
	adjectives = _cached_textdata[TEXT_ADJECTIVES_DICT.name]
	
	# randomly calculating the number of adjectives
	adj_count = 1
	for i in range(max_count-1):
		if not random.randint(0, 5):
			adj_count += 1
	
	result = []
	for _ in range(adj_count):
		adj = random.choice(adjectives)
		if util.chance(0.2):
			adj_part2 = random.choice(adjectives)
			adj = f"{adj[:-2]}о-{adj_part2}"
		if ending:
			adj = adj[:-2] + ending
		result.append(adj)
	
	return " ".join(result)

# for repeating operations encapsulation purposes only
# returns rnd gr with prefix and ending for modifiers
def _get_base_gr(plural=False):
	ensure_cached(TEXT_PREFIXES_DICT)
	prefixes = _cached_textdata[TEXT_PREFIXES_DICT.name]
	
	if plural:
		ensure_cached(TEXT_GRS_PLUR_DICT)
		grs_plur = _cached_textdata[TEXT_GRS_PLUR_DICT.name]
	else:
		ensure_cached(TEXT_GRS_DICT)
		grs = _cached_textdata[TEXT_GRS_DICT.name]
	
	is_prefixed = util.chance(0.15)
	prefix = ""
	if is_prefixed:
		prefix = random.choice(prefixes)
	
	gr = random.choice(grs_plur) if plural else random.choice(grs)
	is_fem = gr.startswith("#")
	is_plur = plural or gr.startswith("@")
	if is_fem:
		gr = gr.lstrip("#")
		return (prefix + gr, "а")
	elif is_plur:
		gr = gr.lstrip("@")
		return (prefix + gr, "і")
	else:
		return (prefix + gr, "ий")