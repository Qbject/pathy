import random, json
import util, gdrive
from util import log
from const import *

class GdriveResourceManager():
	def __init__(self, dir_id):
		self.dir_id = dir_id
		self.set_defaults()
	
	def reload(self):
		self.set_defaults()
	
	def set_defaults(self):
		self._root = None
		self._translations = None
		self._dictionadies = {}
	
	def root(self):
		if not self._root:
			self._root = gdrive.GoogleDriveFile.from_id(self.dir_id)
			self._root.reload(fields="id, mimeType, webContentLink, name")
		return self._root
	
	def get_default_legend_img(self, legend_name):
		return self.root() / "legend" / "default.png"
	
	def get_hate_monday_img(self):
		return (self.root() / "ihatemondays").random_child()
	
	def get_legend_img(self, legend_name):
		legend_img = (self.root() / "legend" / legend_name).random_child()
		return legend_img if legend_img else self.get_default_legend_img()
	
	def get_party_img(self, legends):
		if len(legends) < 1: return None
		if len(legends) == 1: return self.get_legend_img(legends[0])
		return (self.root() / "party" / min(len(legends), 3)).random_child()
	
	def get_full_offline_img(self):
		return (self.root() / "full_offline").random_child()
	
	def get_suatmm_img(self):
		return (self.root() / "shutupandtakemymoney").random_child()
	
	def translations(self):
		if not self._translations:
			translations_path = self.root() / "translations.json"
			self._translations = json.loads(translations_path.read(str))
		return self._translations
	
	def trans(self, txt, default=None):
		if default == None: default = txt
		return self.translations().get(txt, default)
	
	def get_wish(self):
		if util.chance(0.1): # easter wish
			return random.choice(self.dict("wishes")[1:])
		return self.dict("wishes")[0]
	
	def get_moniker(self, noun_v_rod=False, noun_plur=False,
		adj_v_rod=False):
		base, tags = self._get_base_moniker(noun_v_rod, noun_plur)
		adj_ending = self.get_adj_ending(tags, v_rod=adj_v_rod)
		adjectives = self.get_adjectives(ending=adj_ending, min_count=0)

		if \
			not noun_v_rod and \
			not noun_plur and \
			not adjectives and \
			util.chance(0.1) \
		:
			adjectives = "просто"
		
		is_doubled = util.chance(0.05)
		if is_doubled:
			suffix, _ = self._get_base_moniker(noun_v_rod, noun_plur)
			base = f"{base}-{suffix}"
		
		return f"{adjectives} {base}".strip()
	
	# for repeating operations encapsulation purposes only
	# returns rnd noun with prefix and tags
	def _get_base_moniker(self, v_rod=False, plur=False):
		is_prefixed = util.chance(0.05)
		prefix = self.get_dict_rnd("prefixes") if is_prefixed else ""
		
		noun, tags = self.get_noun(v_rod, plur)
		return (prefix + noun, tags)

	def get_count_moniker(self, count):
		if count == 1:
			return f"Соло {self.get_moniker()}"
		adj_v_rod, adj_plur, noun_v_rod, noun_plur = \
			util.get_count_word_props(count)
		moniker = self.get_moniker(noun_v_rod, noun_plur, adj_v_rod)
		return f"{count} {moniker}"

	def get_noun(self, v_rod=False, plur=False):
		if not v_rod and not plur:
			noun_line = self.get_dict_rnd("noun_v_naz")
		elif v_rod and not plur:
			noun_line = self.get_dict_rnd("noun_v_rod")
		if not v_rod and plur:
			noun_line = self.get_dict_rnd("noun_v_naz_plur")
		elif v_rod and plur:
			noun_line = self.get_dict_rnd("noun_v_rod_plur")
		
		noun, *tags = noun_line.split(":")
		if plur and not "p" in tags:
			tags.append("p")
		
		return (noun, tags)

	def get_adj_ending(self, tags, v_rod=False):
		is_fem = "f" in tags
		is_neuter = "n" in tags
		is_plur = "p" in tags
		
		if is_plur:
			return "их" if v_rod else "i"
		if is_fem:
			return "ої" if v_rod else "а"
		if is_neuter:
			return "ого" if v_rod else "е"
		return "ого" if v_rod else "ий"

	def get_adjectives(self, ending=None, min_count=1, max_count=3):
		# randomly calculating the number of adjectives
		adj_count = min_count
		for i in range(max_count - min_count):
			if util.chance(0.3):
				adj_count += 1
		
		# sort of easter egg. 1/500 or 0.002 is a heirloom chance
		if util.chance(0.002):
			adj_count = 10
		
		result = []
		for _ in range(adj_count):
			adj = self.get_dict_rnd("adj")
			if ending:
				adj = adj[:-2] + ending
			result.append(adj)
		
		return " ".join(result)

	def get_goodnight_wish(self, player_name):
		wish = f"Гуд найт, <b>{player_name}</b>\n"
		wish += f"<i>{self.get_adjectives(ending='их')} снів</i> "
		goodnight_emoji = ["🥱", "🛌", "😴", "💤"]
		wish += random.choice(goodnight_emoji)
		return wish

	def get_hokku(self):
		legends = ["Вруф", "Рейфа", "Рейф", "Рампа", "Валькірія", "Ватсон",
		"Лоба", "Бладхаунд", "Лайфа", "Лайфлайн", "Гіба", "Гібралтар", "Октан",
		"Патфайндер", "Хора", "Хорайзон", "Банга", "Ф'юз", "Аша", "Сір",
		"Міраж", "Каустік", "Рева", "Ревенант", "Кріпто", "Нюкасл", "Каталюга"]
		
		lines = []
		for _ in range(3):
			line = self.get_dict_rnd("hokku")
			line = line.format(legend=random.choice(legends))
			lines.append(line)
		return "\n".join(lines)
	
	def dict(self, dict_name):
		if not dict_name in self._dictionadies:
			dict_path = self.root() / "dict" / f"{dict_name}.txt"
			self._dictionadies[dict_name] = dict_path.read(
				str).replace("\r", "").split("\n")
		
		return self._dictionadies[dict_name]
	
	def get_dict_rnd(self, dict_name):
		return random.choice(self.dict(dict_name)).strip()


singleton = GdriveResourceManager(GDRIVE_ASSETS_ID)