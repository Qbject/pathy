# -*- coding: utf-8 -*-

from pathlib import Path
from PIL import Image
import requests, json, random, time, traceback, re, string

def get_rnd_str(length=16):
	return ''.join(random.choice(string.ascii_letters) for x in range(length))

def html_sanitize(text):
	text = text.replace("&", "&amp;")
	text = text.replace("<", "&lt;")
	text = text.replace(">", "&gt;")
	return text

def safe_file_write(file_path, data):
	attempts = 6
	interval = 0.5

	if type(data) == str:
		data = data.encode("utf-8")

	for i in range(attempts):
		try:
			with open(file_path, "wb") as file:
				file.write(data)
			break
		except Exception:
			print("Failed to write file %s (attempt %s)" % (file_path, i))
			time.sleep(interval)

def format_time(seconds_total, include_seconds=False):
	seconds_total = int(seconds_total)
	mins, secs = divmod(seconds_total, 60)
	hours, mins = divmod(mins, 60)
	days, hours = divmod(hours, 24)

	result_str = ""
	if days:
		result_str += "%sдн" % days
	if hours:
		result_str += " %sгод" % hours
	if mins:
		result_str += " %sхв" % mins
	if secs and include_seconds:
		result_str += " %sсек" % secs
	if not result_str:
		result_str = "%sсек" % secs

	return result_str.strip()


def replace_char_map(txt, replacements):
	result_letters = []
	for char in txt:
		result_letters.append(replacements.get(char) or char)
	result_str = "".join(result_letters)
	return result_str

def chance(probability):
	return random.random() < probability

def calc_mid_percentage(targ_num, comp_nums):
	"""
	Really struggle to describe what this func does,
	so you better compile it in your head
	"""
	for i in range(len(comp_nums) - 1):
		prev_num = comp_nums[i]
		next_num = comp_nums[i+1]

		if prev_num <= targ_num < next_num:
			return int(((targ_num - prev_num) / (next_num - prev_num)) * 100)

	return -1

class RandGrGenerator():
	def __init__(self):
		self.GRS_CACHE = None
		self.GRS_PLUR_CACHE = None
		self.MODIFIERS_CACHE = None
		self.PREFIXES_CACHE = None

		self.TARG_DIR = Path(__file__).parent
		self.GRS_FILE_PATH = self.TARG_DIR / "testgen/grs.txt"
		self.GRS_PLUR_FILE_PATH = self.TARG_DIR / "testgen/grs_plur.txt"
		self.MODIFIERS_FILE_PATH = self.TARG_DIR / "testgen/adjectives.txt"
		self.PREFIXES_FILE_PATH = self.TARG_DIR / "testgen/prefixes.txt"

	def get_modifiers(self, ending=None, max_count=3):
		self.ensure_cached_modifiers()

		# randomly calculating the number of modifier words
		modif_count = 1
		for i in range(max_count-1):
			if not random.randint(0, 5):
				modif_count += 1

		modifiers = []
		for modif_n in range(modif_count):
			modif = random.choice(self.MODIFIERS_CACHE)
			if chance(0.2):
				modif_part2 = random.choice(self.MODIFIERS_CACHE)
				modif = f"{modif[:-2]}о-{modif_part2}"
			if ending:
				modif = modif[:-2] + ending
			modifiers.append(modif)

		return " ".join(modifiers)

	def get(self, plural=False):
		is_doubled = chance(0.05)

		gr, modif_ending = self._get_base_gr(plural=plural)
		modifiers = self.get_modifiers(ending=modif_ending)

		if is_doubled:
			suffix_gr, dummy = self._get_base_gr(plural=plural)
			gr = f"{gr}-{suffix_gr}"

		return "%s %s" % (modifiers, gr)

	# for repeating operations encapsulation purposes only
	# returns rnd gr with prefix and ending for modifiers
	def _get_base_gr(self, plural=False):
		self.ensure_cached_prefixes()
		if plural:
			self.ensure_cached_grs_plur()
		else:
			self.ensure_cached_grs()

		is_prefixed = chance(0.15)
		prefix = ""
		if is_prefixed:
			prefix = random.choice(self.PREFIXES_CACHE)

		gr = random.choice(self.GRS_PLUR_CACHE) if plural else random.choice(self.GRS_CACHE)
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

	def ensure_cached_grs(self):
		if not self.GRS_CACHE:
			with open(self.GRS_FILE_PATH, "r", encoding="utf-8") as grs_file:
				lines = grs_file.readlines()
			self.GRS_CACHE = [s.strip() for s in lines]

	def ensure_cached_grs_plur(self):
		if not self.GRS_PLUR_CACHE:
			with open(self.GRS_PLUR_FILE_PATH, "r", encoding="utf-8") as grs_file:
				lines = grs_file.readlines()
			self.GRS_PLUR_CACHE = [s.strip() for s in lines]

	def ensure_cached_modifiers(self):
		if not self.MODIFIERS_CACHE:
			with open(self.MODIFIERS_FILE_PATH, "r", encoding="utf-8") as modifiers_file:
				lines = modifiers_file.readlines()
			self.MODIFIERS_CACHE = [s.strip() for s in lines]

	def ensure_cached_prefixes(self):
		if not self.PREFIXES_CACHE:
			with open(self.PREFIXES_FILE_PATH, "r", encoding="utf-8") as prefixes_file:
				lines = prefixes_file.readlines()
			self.PREFIXES_CACHE = [s.strip() for s in lines]

class PathyState():
	def __init__(self):
		self._state_data = None
		self.state_path = Path(__file__).parent / "data/legacy_state.json"
		self.is_modified = False

	def read(self):
		with open(self.state_path, "r") as state_file:
			self._state_data = json.loads(state_file.read())
		self.is_modified = False

	def get(self, path):
		if not self._state_data:
			self.read()

		if type(path) != list: path = [path]
		subpath_value = self._state_data
		for path_step in path:
			if not type(subpath_value) == dict:
				return None
			if not path_step in subpath_value:
				return None
			subpath_value = subpath_value[path_step]

		return subpath_value

	def set(self, path, value):
		if not self._state_data:
			self.read()

		if type(path) != list: path = [path]
		subpath_value = self._state_data

		for i, path_step in enumerate(path):
			if not type(subpath_value) == dict:
				return False

			is_last_step = i == len(path) - 1
			if is_last_step:
				subpath_value[path_step] = value
				self.is_modified = True
				return True

			if not path_step in subpath_value:
				subpath_value[path_step] = {}
			subpath_value = subpath_value[path_step]

		return False

	def save(self):
		# for now it is possible to bypass set method by changing dictionaries by reference
		# eg a = get("field"); a["subfield"] = "new_value"
		#if self.is_modified:
		safe_file_write(self.state_path, json.dumps(self._state_data, indent="\t"))
		self.is_modified = False

class PathyRobot():
	def __init__(self):
		self.MOZAM_API_KEY = "***REMOVED***"
		self.TARG_CHAT_ID = ***REMOVED*** # ASL
		self.DEBUG_CHAT_ID = ***REMOVED*** # pathy debug
		self.BOT_TOKEN = "***REMOVED***"
		self.NEWS_QUERY_INTERVAL = 60 * 60
		self.BOT_USERNAME = "***REMOVED***"
		self.MONDAY_IMG_ID = "AgACAgIAAx0CTJBx5QADHWEiP2LrqUGngEIIOJ4BNUHmVk_4AAJntTEboQ8RSVxQerfln3yYAQADAgADeQADIAQ"
		self.OFFLINE_FOR_SURE_TIMEOUT = 60 * 15
		self.DEBUG_LOG_EXITS = True
		self.dl_proxy_chat_id = ***REMOVED***
		self.status_msg_delim = "--- --- ---"


		self.cur_dir = Path(__file__).parent
		self.cache_dir = self.cur_dir / "data/cache"

		self.cache_dir.mkdir(exist_ok=True)

		self.state = None
		self.update_whitelisted_chats = (
			self.TARG_CHAT_ID,
			self.DEBUG_CHAT_ID
		)

		self.rnd_gr = RandGrGenerator()
		self.state = PathyState()

		self.who_to_pick_replies = (
			"Бери собаку, винюхуй кемперів, насолоджуйся волхаками, покажи всім в кого тут найбільший Олфазер!",
			(
				"Бери Гібу! Чави, танкуй, жуй!",
				"Бери Гібу! Цей варіант ідеально підходить якщо ти рішив показати всім хто тут самий мужицький мужик братец)"
			),
			(
				"Раджу Лайфлун, вона чудово підходить для підривання пуканів і пінгування мозамбіків :)",
				"Пікай Че:)) Ну Аджей Че, ну лайфілайн всенсі - найкращого сапорта в іграх АРЕХ, ііі єдиного..."
			),
			"Візьми мене! Граплі - це дуже весело! А от хітбокс як у Гіби - не дуже :(",
			"Бери Вруф. Кнопка \"Я не хочу умирати!\" і хітбокс як у 1 ноги Гіби зайвими не бувають",
			"Пікни бангу. Якщо наловиш пуль зможеш казати \"Це так задумано, я хотів забуститись\"",
			"Спробуй газового діда, газу повні штани...",
			(
				"Пікни Міража і покажи, хто тут король бамбузлінгу. А можливість ресати в невидимості часом рішає",
				"Юю гат бамбузелт, лук ет ю))) ну ти поняв що зробити"
			),
			"Не думай, бери Октана. І взагалі, граючи на Октані думати не прийнято",
			(
				"Спробуй Електробабу. Армія Нессі - імба і не контриться",
				"Візьми електро-вайфу - підніми пікрейт"
			),
			"Візьми корейця, на ньому весело - можна ресати тімейтів через пів карти, відкривати двері з іншої сторони, дивитись з висоти пташиного польоту, зносити щити через стіну, вислуховувати тімейтів що вмерли 2в3...",
			(
				"Візьми Реву і покажи кожаним мішкам, що таке страждання (тільки не на собі)",
				"Візьми Реву, він теж робот як і я... але без грапель... і без настрою"
			),
			"Бери Лобу і забирай кращий лут навколо. Убивши тебе вороги скажуть \"Дякую\"",
			"Бери Рампу і влаштуй їм Фортнайт",
			"Візьми Хору і всасуй ще й чорною дирою!",
			"Раджу Ф'юза якщо захотілось попідривати пукани буквально",
			"Політай на Валькірії. Літати все ж цікавіше, ніж... не літати",
			"Бери Факінг Волхакера. Чесний геймплей для слабаків!"
		)

		self.translations = {
			"Rookie": "<s>Нуб</s> Новачок",
			"Bronze": "Бронза",
			"Silver": "Сільвер",
			"Gold": "Золото",
			"Platinum": "Платина",
			"Diamond": "Даймонд",
			"Master": "Мастер",
			"Apex Predator": "Предатор",
			"teammates_lifted": "Запущені на ліфті тімейти",
			"arenas_damage": "Дамаг на аренах",
			"revive_shield_damage_blocked": "Заблочений дамаг ревайв щитом",
			"silenced_targets_kills": "Засайленсяні кіли",
			"dome_damage_blocked": "Заблочений куполом дамаг",
			"games_played": "Зіграні ігри",
			"arenas_kills": "Кіли на аренах",
			"sniper_kills": "Кіли зі снуперок",
			"wins_season_10": "Віни в сезоні 10",
			"winning_kills": "Виграшні кіли",
			"wins_season_5": "Віни в сезоні 5",
			"death_totems": "Тотеми смерті",
			"headshots": "Хеди",
			"specialEvent_wins": "Віни",
			"wins_season_4": "Віни в сезоні 4",
			"grandsoiree_wins": "Віни",
			"rifts_squadmates_phased": "Зателепорчені тімейти",
			"damage": "Дамаг",
			"ultimate_damage": "",
			"grapple_travel_distance": "Метри на граплі",
			"specialEvent_damage": "Дамаг",
			"kills_season_6": "Кіли в сезоні 6",
			"care_package_kills": "Кіли стволами з дропу",
			"smg_kills": "Кіли з пп",
			"grenades_distance": "",
			"silenced_targets": "Засайленсяні вороги",
			"noxgassed_enemies_killed": "Загазовані кіли",
			"distance_on_stim": "Метрів під ЛСД",
			"wins_season_6": "Віни в сезоні 6",
			"wins_season_3": "Віни в сезоні 3",
			"arenas_wins": "Віни на аренах",
			"pinged_passive_loot": "",
			"wins_season_2": "Віни в сезоні 2",
			"special_arenas_kills": "Кіли на аренах",
			"ar_kills": "Кіли з вінтовок",
			"traps_destroyed": "",
			"wins_season_9": "Віни в сезоні 9",
			"specialEvent_kills": "Кіли",
			"dropped_items_for_squadmates": "Предмети для тімейтів",
			"lmg_kills": "Кіли з пуліків",
			"kills_season_5": "Кіли в сезоні 5",
			"ultimate_exhibit_enemies_inside": "Заволхакані враги",
			"noxgas_damage_dealt": "Дамаг газом",
			"tactical_tp_distance": "Метрів телепортнуто",
			"pistol_kills": "Кіли з пістолів",
			"smoke_grenade_enemies_hit": "Бахнуті димом враги",
			"kills_season_10": "Кіли в 10 сезоні",
			"wins_season_1": "Віни в сезоні 1",
			"wins_as_full_squad": "Віни фул сквадом",
			"soft_landings": "М'які приземлення",
			"knuckle_cluster_hits": "Враги, бахнуті петардою",
			"doc_drone_squadmates_revived": "Ревайвнуті доком тімейти",
			"kills_season_7": "Кіли в сезоні 7",
			"shotgun_kills": "Кіли з дробашів",
			"bombardment_kills": "Кіли артою",
			"double_time_distance": "Метрів на спідах",
			"damage_season_1": "Дамаг в сезоні 1",
			"vtol_distance_travelled": "Метрів на джетпаку",
			"passive_enemy_heartbeats_heard": "Враги почуті пасівкою",
			"skyward_dive_allies_repositioned": "Тімейти, запущені в космос",
			"kills_season_8": "Кіли в сезоні 8",
			"voice_warnings_heard": "Почуто голосів",
			"revives": "Ревайви",
			"damage_blocked": "Заблочений дамаг",
			"ultimate_bullets_fired": "Шоти з ульти",
			"passive_enemies_scanned": "Скани пасівкою",
			"shields_charged": "Заряжені щити",
			"noxgas_times_activated": "Активації бочок",
			"squadmates_use_jumppad": "Забатучені тімейти",
			"ultimate_loot_taken": "Лут з ульти",
			"beast_of_the_hunt_kills": "Кіли в режимі рембо",
			"top_3": "Топи 3",
			"missile_swarm_enemies_hit": "Попадання залпом",
			"wins_season_7": "Віни в сезоні 7",
			"kills_as_kill_leader": "Кіли як кіл лід",
			"motherlode_captured": "Зажарені супостати",
			"gunshield_damage_blocked": "Дамаг заблочений щитом",
			"enemies_scanned": "Засканені вруги",
			"wins_season_8": "Віни в сезоні 8",
			"kills_season_1": "Кіли в сезоні 1",
			"doc_drone_healing": "Хп захілено дроном",
			"encore_execution_escaped": "Побіги під ультою",
			"grandsoiree_damage": "Дамаг",
			"ziplines_used_by_squad": "Використань зіпки тімейтами",
			"airdrops_looted": "Залутані дропи",
			"detected_breaches": "Прожарки заборами",
			"creeping_barrage_damage": "Дамаг артою",
			"tactical_focus_of_attention_hits": "Попадання тактикою",
			"phase_walk_time": "Час в пустоту",
			"kills": "Кіли",
			"beacons_scanned": "Маяків засканено",
			"bullets_amped": "Пуль підсилено",
			"traps_scanned": "Засканено трапів",
			"special_arenas_damage": "Дамаг на аренах",
			"decoys_spawned": "Приманки",
			"special_arenas_wins": "Віни на аренах",
			"grandsoiree_kills": "Кіли",
			"shield_damage": "",
			"passive_health_regen": "Відрегенено хп",
			"executions": "Казні",
			"ordnance_destroyed": "Збито рандомного дєрьма",
			"bamboozles": "Бамбузли",
			"marksman_kills": "Кіли з марксманів",
			"kills_season_9": "Кіли в сезоні 9",
			"kills_season_11": "Кіли в сезоні 11",
			"wins_season_11": "Віни в сезоні 11",
			"kills_season_12": "Кіли в сезоні 12",
			"wins_season_12": "Віни в сезоні 12",
			"on_Revenant": "Реві ☠️",
			"on_Crypto": "암호화 짜증 💻",
			"on_Horizon": "Космобабі 🌠",
			"on_Gibraltar": "наГібі 🐖",
			"on_Wattson": "Багеті 🔌",
			"on_Fuse": "Бабах-діду 🧨",
			"on_Bangalore": "Бангі 🚬",
			"on_Wraith": "Вруф 🥷🏻",
			"on_Octane": "Наркомані 🤪",
			"on_Bloodhound": "Собаці 🦮",
			"on_Caustic": "Газовому діду 🤢",
			"on_Lifeline": "Лайфі 🥁",
			"on_Pathfinder": "Паті 🦾",
			"on_Loba": "Лобі 💋",
			"on_Mirage": "Міражу 👯‍♂️",
			"on_Rampart": "Рампі 🔧",
			"on_Valkyrie": "Факінг Валькірії вжух-вжух хер попадеш 🧚‍♀️",
			"on_Seer": "Волхакері 👁",
			"on_Ash": "Аші ⚔️",
			"on_Mad Maggie": "Огонь-бабі 🔥",
			"on_Global": "Всіх і зразу",
			"on_Newcastle": "НьюКазлі 🛡",
			"Kings Canyon": "Коньйон",
			"World's Edge": "Край світу",
			"Worlds Edge": "Край світу", # for some reason this variant also happens
			"Olympus": "Олімп",
			"Phase runner": "Фейз раннер",
			"Oasis": "Оазис",
			"Overflow": "Оверфлоу",
			"Party crasher": "Паті Крашер",
			"Dome": "Купол",
			"Hillside Outpost": "Пустельне село",
			"offline": "Офлайн",
			"inLobby": "В Лобі",
			"inMatch": "В матчі",
			"optic_hcog_ranger": "3x приціл",
			"shatter_caps": "Розривні (пердаки)",
			"knockdown_shield": "Нокдаун щит",
			"mobile_respawn_beacon": "Мобільна ресалка",
			"med_kit": "Медкіт",
			"large_shield_cell": "Акум",
			"shotgun_bolt": "Шатган болт",
			"dual_shell": "Подвійне дно",
			"extended_light_mag": "Лайт маг",
			"optic_variable_aog": "2х-4х оптика",
			"backpack": "Пакет",
			"helmet": "Шляпа 🎩",
			"extended_heavy_mag": "Хардбас",
			"boosted_loader": "Бустед лоадер",
			"optic_variable_sniper": "4х-8х оптика",
			"extended_sniper_mag": "Снайп маг",
			"standard_stock": "Приклад",
			"extended_energy_mag": "Енергомаг",
			"optic_digital_threat": "Цифровий 1х",
			"optic_hcog_bruiser": "2x оптика",
			"barrel_stabilizer": "СосиСка",
			"turbocharger": "Турбочача 🌪",
			"hammerpoint_rounds": "Хамерпоінти",
			"sniper_stock": "Снайперський приклад",
			"kinetic_loader": "Кінетік фідер",
		}

	def trans(self, phrase):
		if phrase in self.translations:
			return self.translations[phrase]
		else:
			return phrase

	def format_rank(self, rank_dict, mode="br"):
		points_name = "RP" if mode == "br" else "AP"

		if rank_dict["rankName"] == "Apex Predator":
			return f"Предатор #{rank_dict['ladderPosPlatform']}"
		if rank_dict["rankName"] == "Master":
			return f"Мастер ({rank_dict['rankScore']}{points_name})"

		rank_data = {
			"br": [
				0, 250, 500, 750,
				1000, 1500, 2000, 2500,
				3000, 3600, 4200, 4800,
				5400, 6100, 6800, 7500,
				8200, 9000, 9800, 10600,
				11400, 12300, 13200, 14100,
				15000
			],
			"arena": [
				0, 400, 800, 1200,
				1600, 2000, 2400, 2800,
				3200, 3600, 4000, 4400,
				4800, 5200, 5600, 6000,
				6400, 6800, 7200, 7600,
				8000
			]
		}

		next_percentage = calc_mid_percentage(
			rank_dict["rankScore"], rank_data[mode])
		return "%s %s (%s%%)" % (
			self.trans(rank_dict["rankName"]),
			rank_dict["rankDiv"],
			next_percentage
		)

	def get_session_summary(self, online_since, online_to, stat_before, stat_after, session_matches):
		result = ""
		duration = online_to - online_since
		result += "<b>Зіграно часу</b>: %s\n" % format_time(duration)

		if session_matches:
			result += "<b>Матчів зіграно</b>: %s\n" % len(session_matches)

		#legends_matches = {}
		#for match in session_matches:
		#    legend = match["legend"]
		#    if not legend:
		#        continue
		#
		#    if not legends_matches.get(legend):
		#        legends_matches[legend] = 0
		#    legends_matches[legend] += 1
		#
		#for legend, matches in legends_matches.items():
		#    result += "<b>Матчів на %s</b>: %s\n" % (
		#        self.trans("on_"+legend), matches)

		if stat_before["global"]["level"] != stat_after["global"]["level"] or \
		stat_before["global"]["toNextLevelPercent"] != stat_after["global"]["toNextLevelPercent"]:
			result += "<b>Левел</b>: %s → %s\n" % (
				stat_before["global"]["level"] + stat_before["global"]["toNextLevelPercent"] / 100,
				stat_after["global"]["level"] + stat_after["global"]["toNextLevelPercent"] / 100
			)

		br_rank_diff = stat_after["global"]["rank"]["rankScore"] - stat_before["global"]["rank"]["rankScore"]
		if br_rank_diff:
			rank_before = self.format_rank(stat_before["global"]["rank"], mode="br")
			rank_after  = self.format_rank(stat_after["global"]["rank"], mode="br")
			result += "<b>Ранг в БР</b>: %s → %s\n" % (rank_before, rank_after)

		arena_rank_diff = stat_after["global"]["arena"]["rankScore"] - stat_before["global"]["arena"]["rankScore"]
		if arena_rank_diff:
			rank_before = self.format_rank(stat_before["global"]["arena"], mode="arena")
			rank_after  = self.format_rank(stat_after["global"]["arena"], mode="arena")
			result += "<b>Ранг в аренах</b>: %s → %s\n" % (rank_before, rank_after)

		trackers = {
			"before": self.get_trackers(stat_before),
			"after": self.get_trackers(stat_after)
		}

		for legend_name in trackers["before"]:
			legend_summary = ""

			legend_summary += "<b>На %s</b>:\n" % self.trans(f"on_{legend_name}")

			matches = len([m for m in session_matches if m["legend"] == legend_name])
			legend_summary += "  <b>Матчів зіграно</b>: %s\n" % matches

			activity_seen = bool(matches)
			for tracker_name in trackers["before"][legend_name]:
				if not tracker_name in trackers["after"][legend_name]:
					continue
				val_before = trackers["before"][legend_name][tracker_name]["value"]
				val_after = trackers["after"][legend_name][tracker_name]["value"]
				diff = val_after - val_before
				if not diff: continue
				legend_summary += "  <b>%s</b>: %s" % (self.trans(tracker_name), diff)
				if (diff % 1000) == 300:
					legend_summary += "  </pre><span class='tg-spoiler'>ВІДСОСИ У КРАБЕРИСТА</span><pre>"
				else:
					legend_summary += "\n"
				activity_seen = True

			if activity_seen:
				result += legend_summary

		return result.strip()

	def get_trackers(self, player_stats):
		"Remaking data structure to make work with trackers easier"
		result_dict = {}
		for legend_name, legend in player_stats["legends"]["all"].items():
			if not "data" in legend: continue
			result_dict[legend_name] = {}
			for tracker in legend["data"]:
				result_dict[legend_name][tracker["key"]] = tracker
		return result_dict

	def call_tg_api(self, method, params = {}, files = {}):
		response_raw = requests.post("https://api.telegram.org/bot{}/{}".format(self.BOT_TOKEN, method), data=params, files = files).text
		response = json.loads(response_raw)
		if not "result" in response or \
		not response["ok"]:
			raise Exception("Botapi result['ok'] == False:\n" + json.dumps(response, indent = "\t"))
		return response["result"]

	def notify(self, text, is_debug=False):
		targ_chat = self.DEBUG_CHAT_ID if is_debug else self.TARG_CHAT_ID
		self.call_tg_api("sendMessage", {"chat_id": targ_chat, "text": text, "parse_mode": "HTML"})

	def pathy_upd(self):
		if not self.state.get("news"):
			self.state.set(["news"], {
				"last_query": 0,
				"last_link": "https://www.ea.com/ru-ru/games/apex-legends/news/emergence-worlds-edge-map-update"
			})
		if int(time.time()) - self.state.get(["news", "last_query"]) > self.NEWS_QUERY_INTERVAL:
			pass
			#self.news_upd()

		self.players_upd()
		self.delayed_msgs_upd()

		self.state.set(["last_upd"], time.asctime())
		self.state.save()

	def add_delayed_msg(self, msg_text, after_seconds, name):
		if not self.state.get("delayed_msgs"):
			self.state.set("delayed_msgs", [])

		delayed_msgs = self.state.get("delayed_msgs")
		delayed_msgs.append({
			"time": int(time.time()) + after_seconds,
			"text": msg_text,
			"name": name
		})

	def remove_delayed_msg(self, msg_name):
		if not self.state.get("delayed_msgs"):
			self.state.set("delayed_msgs", [])
		delayed_msgs = self.state.get("delayed_msgs")

		msg_i_to_remove = None
		for i, msg in enumerate(delayed_msgs):
			if msg["name"] == msg_name:
				msg_i_to_remove = i
				break

		if type(msg_i_to_remove) == int:
			delayed_msgs.pop(msg_i_to_remove)

	def delayed_msgs_upd(self):
		time_now = int(time.time())
		if not self.state.get("delayed_msgs"):
			self.state.set("delayed_msgs", [])
		delayed_msgs = self.state.get("delayed_msgs")
		to_remove = []

		for msg_i, msg in enumerate(delayed_msgs):
			if time_now < msg["time"]:
				continue

			self.call_tg_api("sendMessage", {"chat_id": self.TARG_CHAT_ID, "text": msg["text"], "parse_mode": "HTML"})
			#self.call_tg_api("sendMessage", {"chat_id": self.DEBUG_CHAT_ID, "text": msg["text"], "parse_mode": "HTML"})
			to_remove.append(msg_i)

		for msg_i in reversed(to_remove):
			delayed_msgs.pop(msg_i)

	def players_upd(self):
		stats = self.fetch_players_stats()

		players_online = 0
		someone_become_online = False
		for player in stats:
			# weird complicated logic due to strange api responses sometimes
			is_online = bool(\
				player["realtime"]["isOnline"] and (\
					player["realtime"]["currentState"] != "offline" or \
					player["realtime"]["currentStateSinceTimestamp"] != -1 \
				) \
			)
			if is_online: players_online += 1
			player_uid = str(player["global"]["uid"])
			player_state = self.state.get(["players", player_uid])
			if not player_state:
				self.state.set(["players", player_uid], {})
				player_state = self.state.get(["players", player_uid])
			player_state["name"] = player["global"]["name"]

			was_banned = bool(player_state.get("is_banned"))
			try:
				is_banned = player_state["is_banned"] = player["global"]["bans"]["isActive"]
			except Exception:
				is_banned = player_state["is_banned"] = False

			if not was_banned and is_banned:
				ban_notification = "<b>%s</b> отримав <i>%s</i> банан :/" % (player_state["name"], self.rnd_gr.get_modifiers())
				ban_reason = player["global"].get("bans") and player["global"]["bans"].get("last_banReason")
				unban_after = player["global"].get("bans") and player["global"]["bans"].get("remainingSeconds")
				if ban_reason:
					ban_notification += "\n<i>Причина: %s</i>" % ban_reason
				if unban_after:
					ban_notification += "\n<i>Закінчиться через: %s</i>" % format_time(unban_after)
				self.notify(ban_notification)

			if was_banned and not is_banned:
				unban_notification = "У <b>%s</b> нарешті спав банан :)" % player_state["name"]
				self.notify(unban_notification)

			if player_state.get("stats_when_entered"):
				self.merge_player_trackers(
					player_state["stats_when_entered"],
					player
				)

			if player["realtime"]["currentState"] == "inMatch":
				if not "session_matches" in player_state:
					player_state["session_matches"] = []

				cur_match = {}
				cur_match["ts"] = player["realtime"]["currentStateSinceTimestamp"]
				cur_match["legend"] = player["realtime"].get("selectedLegend")

				last_match = None
				if player_state["session_matches"]:
					last_match = player_state["session_matches"][-1]

				if last_match:
					# here we ensuring that the match is really new. Sometimes
					# timestamp of the same match may be +- a few seconds
					if abs(cur_match["ts"] - last_match["ts"]) > 20:
						player_state["session_matches"].append(cur_match)
					else:
						# if there are different legends before and after legend select
						# (10-20 seconds after match start) then we prioritize latter
						last_match["legend"] = cur_match["legend"]
				else:
					player_state["session_matches"].append(cur_match)

			was_online = player_state.get("is_online")
			if not was_online and is_online:
				offline_time = int(time.time()) - (player_state.get("offline_since") or 0)
				offline_for_sure = offline_time > self.OFFLINE_FOR_SURE_TIMEOUT
				someone_become_online |= offline_for_sure

				if not offline_for_sure:
					last_gr = player_state.get("last_gr") or "грун"
					msg_text = "А ні, <b>%s</b> досі <i>%s</i>" % (player["global"]["name"], last_gr)
				else:
					rnd_gr = self.rnd_gr.get()
					player_state["last_gr"] = rnd_gr

					wish = "Гуд лак, хев фан, донт дай! :)"
					easter_wishes = [
						"Гуд лак, хев фан, Джедай! :)",
						"Гуд лак, хев фан, донт дай! -_-",
						"Гуд лак, хев фан, донт дай! ))0)00))0)))0)))00))",
						"Гии",
						"Гуд фак, хев фан, донт дай! :)",
						"Гуд лак, хев фак, донт дай! :)",
						"Гуд лаг, хев фан, донт дай! :)",
						"Гуд лак, хев фан, лайтів дай! :)",
						"Гуд лак, хев фан, крабу віддай! :)",
						"Гуд лав, хев фан, донт дай! :)",
						"Гуд лак, хев фан, дай мазафака дай мазафака дай! :)",
						"Гуд!",
						"Гуд лак, хев фан, гараж продай! :)",
						"Гуд лак, хев фан, ни слова по-русски..."
					]
					if chance(0.2):
						wish = random.choice(easter_wishes)

					offline_since = player_state.get("offline_since")
					msg_text = "<b>%s</b> тепер <i>%s</i> після %s відпочинку\n<i>%s</i>" % (
						player["global"]["name"],
						rnd_gr,
						format_time(
							int(time.time()) - int(offline_since)
						) if offline_since else "довгого",
						wish
					)
				(not self.state.get(["shush_mode"])) and self.notify(msg_text)

				player_state["is_online"] = 1
				player_state["online_since"] = int(time.time())
				player_state["offline_since"] = None
				player_state["stats_when_entered"] = player

				self.remove_delayed_msg(f"goodnight_{player_uid}")
			elif was_online and not is_online:
				summary = self.get_session_summary(
					player_state["online_since"],
					int(time.time()),
					player_state["stats_when_entered"],
					player,
					player_state["session_matches"]
				)

				if self.DEBUG_LOG_EXITS:
					try:
						debug_msg = "%s went offline\nMatches: %s\nRealtime resp:\n<pre>%s</pre>" % (
							player["global"]["name"],
							json.dumps(player_state["session_matches"], indent="\t"),
							json.dumps(player["realtime"], indent="\t")
						)
						self.notify(debug_msg, is_debug=True)
					except Exception:
						print(traceback.format_exc())

				last_gr = player_state.get("last_gr") or "грун"
				#msg_text = "<b>%s</b> походу все... Як гралось? Багато задоволення отримав?\n<pre>%s</pre>" % (player["global"]["name"], summary)
				msg_text = "<b>%s</b> більше не <i>%s</i> :(\n<pre>%s</pre>" % (player["global"]["name"], last_gr, summary)
				(not self.state.get(["shush_mode"])) and self.notify(msg_text)
				player_state["is_online"] = 0
				player_state["online_since"] = None
				player_state["offline_since"] = int(time.time())
				player_state["stats_when_entered"] = {}
				player_state["session_matches"] = []

				# goodnight
				hour_now = (time.gmtime().tm_hour + 3) % 24 # 00:00 MSK, 23:00 Kyiv
				# working only at 00-05
				if hour_now <= 5:
					self.add_delayed_msg(
						f"Гуд найт, {player['global']['name']}", 60 * 15,
						f"goodnight_{player_uid}")

		if someone_become_online:
			self.on_new_online(players_online)

	def on_new_online(self, online_count):
		party_events = {
			"2": [
				{
					"img_id": "AgACAgIAAx0CTJBx5QACCzxiERiVOB0EJpmResfZTtGByT2YHQACYrgxG1giiUhSAogdvEY_agEAAwIAA3gAAyME",
					"caption": "Два <i>{gr}</i>!"
				},
				{
					"img_id": "AgACAgIAAx0CTJBx5QACCz5iERipxxyoF-CHgt_U2NT4zYR2NwACZLgxG1giiUhHcGApuKhAKwEAAwIAA3gAAyME",
					"caption": "Два <i>{gr}</i>!"
				},
			],
			"3": [
				{
					"img_id": "AgACAgIAAx0CTJBx5QADJWEiQpfuE70QwP-UyBZ4oznLIst0AAJqtTEboQ8RSRqS7nyEQMYMAQADAgADeQADIAQ",
					"caption": "Три <i>{gr}</i>!"
				},
				{
					"img_id": "AgACAgIAAx0CTJBx5QACCzpiERhyg6FkRR0FyiXj9c-hqd039wACYLgxG1giiUj-RWB2M5vlwwEAAwIAA3kAAyME",
					"caption": "Три <i>{gr}</i>!"
				},
			]
		}

		count_events = party_events.get(str(online_count))
		if count_events:
			party_event = random.choice(count_events)
		else:
			return

		self.call_tg_api("sendPhoto", {
			"chat_id": self.TARG_CHAT_ID,
			"photo": party_event["img_id"],
			"parse_mode": "HTML",
			"caption": party_event["caption"].format(gr=self.rnd_gr.get(plural=True))
		})

	def merge_player_trackers(self, stat1, stat2):
		"Adds missing trackers to stat1 from stat2"

		def is_tracker_saved(legend_name, tracker_key):
			if not stat1["legends"]["all"][legend_name].get("data"):
				return False
			return bool(list(filter(
				lambda tracker: tracker.get("key") == tracker_key,
				stat1["legends"]["all"][legend_name]["data"]
			)))

		for legend_name, legend in stat2["legends"]["all"].items():
			if not legend.get("data"): continue
			for tracker in legend["data"]:
				if not is_tracker_saved(legend_name, tracker["key"]):
					if not stat1["legends"]["all"][legend_name].get("data"):
						stat1["legends"]["all"][legend_name]["data"] = []
					stat1["legends"]["all"][legend_name]["data"].append(tracker)

	def news_upd(self):
		self.state.set(["news", "last_query"], int(time.time()))
		news_to_notify = []
		news = requests.get("https://api.mozambiquehe.re/news?lang=ru_ru&auth=%s" % self.MOZAM_API_KEY).json()
		for news_item in news:
			if not news_item["link"] == self.state.get(["news", "last_link"]):
				news_to_notify.append(news_item["link"])
			else:
				self.state.set(["news", "last_link"], news[0]["link"])
				break

		news_to_notify.reverse()
		news_to_notify = news_to_notify[-3:]
		for link in news_to_notify:
			self.notify(link)

	def on_tg_update(self, update):
		def reply(text, use_html=True):
			self.call_tg_api(
				"sendMessage",
				{
					"chat_id": chat_id,
					"text": text,
					"parse_mode": "HTML" if use_html else None
				}
			)

		if not "message" in update:
			return
		chat_id = update["message"]["chat"]["id"]
		if chat_id == self.DEBUG_CHAT_ID:
			if update["message"]["text"].startswith("ctl "):
				import ctl
				cmd_arr = update["message"]["text"].split(" ")
				cmd = cmd_arr[1]
				args_raw = " ".join(cmd_arr[2:])
				if args_raw:
					args = json.loads(args_raw)
				else:
					args = {}
				
				cmd_resp = ctl.entry(cmd, args) or "<empty>"
				reply(cmd_resp, use_html=False)
				return

			msg_json = html_sanitize(json.dumps(update["message"], indent="\t"))
			self.call_tg_api(
				"sendMessage",
				{
					"chat_id": chat_id,
					"text": "%s\n<pre>%s</pre>" % (
						"  %s\n  %s\n  %s" % (
							"<span class='tg-spoiler'>SPOILER</span><s>sss</s>",
							#self.rnd_gr.get(),
							self.rnd_gr.get(),
							self.rnd_gr.get(plural=True)
						),
						msg_json
					),
					"parse_mode": "HTML"
				}
			)
			#self.call_tg_api("sendMessage", {"chat_id": chat_id, "text": "%s" % self.rnd_gr.get(), "parse_mode": "HTML"})
		if not chat_id in self.update_whitelisted_chats:
			return
		if not update["message"].get("text"):
			return

		command, params = self.parse_bot_command(update["message"]["text"])

		if command == "/status":
			try:
				status_msg = self.get_status_msg()
				self.state.save()
			except Exception:
				status_msg = "Тут якась діч, не можу отримати статус :("
				print(traceback.format_exc())
			self.call_tg_api("sendMessage", {"chat_id": chat_id, "text": status_msg, "parse_mode": "HTML"})

		if command == "/fuck":
			targ_txt = ""
			if update["message"].get("reply_to_message"):
				targ_msg = update["message"]["reply_to_message"]
				if targ_msg.get("text"):
					targ_txt = targ_msg["text"]
			else:
				targ_txt = params

			if targ_txt.strip():
				try:
					resp = html_sanitize(self.marsian_to_ua(targ_txt))
				except Exception:
					print(traceback.format_exc())
					resp = "Тут якась діч, не можу перекласти :("
			else:
				resp = "Потрібно написати типу <b>/fuck Afr wtq vfhcsfycmrbq</b>"

			self.call_tg_api("sendMessage", {"chat_id": chat_id, "text": resp, "parse_mode": "HTML"})

		if command == "/who_to_pick":
			chosen_legend = random.choice(self.who_to_pick_replies)
			if type(chosen_legend) == tuple:
				reply = random.choice(chosen_legend)
			else:
				reply = chosen_legend
			self.call_tg_api("sendMessage", {"chat_id": chat_id, "text": reply, "parse_mode": "HTML"})

		if command == "/shush":
			shush_mode = bool(self.state.get(["shush_mode"]))
			tgl_shush_mode = not shush_mode
			self.state.set(["shush_mode"], tgl_shush_mode)
			self.state.save()

			msg = "Ок, мовчун" if tgl_shush_mode else "Ок, говорун"
			self.call_tg_api("sendMessage", {"chat_id": chat_id, "text": msg, "parse_mode": "HTML"})

	def parse_bot_command(self, msg_text):
		command_search = re.findall("^(/[a-zA-Z0-9_]+)(@[a-zA-Z0-9_]+){0,1}", msg_text)
		if not command_search:
			return (None, None)

		command = command_search[0][0]
		botname = command_search[0][1]
		if botname and botname.lower() != "@"+self.BOT_USERNAME.lower():
			return (None, None)

		full_command_len = len(command)+len(botname)
		params = msg_text[full_command_len:].strip()

		return (command, params)

	def get_status_msg(self):
		def get_stat_by_uid(uid):
			for player_stat in all_stats:
				if uid == str(player_stat["global"]["uid"]):
					return player_stat

		all_stats = self.fetch_players_stats()
		result_msg = ""
		for uid, player in self.state.get(["players"]).items():
			is_last_item = list(self.state.get(["players"]).keys())[-1] == uid
			player_stats = get_stat_by_uid(uid)

			if player.get("is_online"):
				result_msg += "<b>%s</b> <i>%s</i> \n<i>%s</i>\n<pre>%s</pre>\n" % (
					player["name"],
					player.get("last_gr") or "грун",
					self.get_realtime_status(player_stats["realtime"]),
					self.get_session_summary(
						player["online_since"],
						int(time.time()),
						player["stats_when_entered"],
						player_stats,
						player["session_matches"]
					).strip()
				)
				if not is_last_item: result_msg += self.status_msg_delim + "\n"
			else:
				result_msg += "<b>%s</b>\n<i>Напевно зайнятий більш корисними справами, ніж Апекс</i>\n" % player["name"]
				if player["offline_since"]:
					time_offline = format_time(int(time.time()) - player["offline_since"])
				else:
					time_offline = "давно"
				result_msg += "<i>Не заходив уже %s</i>\n" % time_offline
				if not is_last_item: result_msg += self.status_msg_delim + "\n"
		result_msg += "\n"

		try:
			result_msg += self.get_map_rotation()
		except Exception:
			print(f"Failed to get map rotation. Traceback: {traceback.format_exc()}")
			result_msg += "Ротацію карт не вдається отримати :("
		result_msg += "\n\n"
		try:
			result_msg += self.get_crafting_rotation()
		except Exception:
			print(f"Failed to get craft rotation. Traceback: {traceback.format_exc()}")
			result_msg += "Ротацію крафту не вдається отримати :("

		return result_msg

	def get_map_rotation(self):
		def _format_map_rotation(mode_name, rotation_stats):
			return "%s зараз на карті <b>\"%s\"</b>\n<i>Через %s перейде на <b>%s</b>, де буде %s</i>\n" % (
				mode_name,
				self.trans(rotation_stats["current"]["map"]),
				format_time(rotation_stats["current"]["remainingSecs"]),
				self.trans(rotation_stats["next"]["map"]),
				format_time(rotation_stats["next"]["DurationInSecs"])
			)

		map_rotation_resp = requests.get("https://api.mozambiquehe.re/maprotation?version=5&auth=%s" % self.MOZAM_API_KEY).json()

		map_rotation_text = ""
		map_rotation_text += _format_map_rotation("БР", map_rotation_resp["battle_royale"]) + self.status_msg_delim + "\n"
		map_rotation_text += "БР ранкед зараз на карті <b>%s</b>\n" % (
			self.trans(map_rotation_resp["ranked"]["current"]["map"])
		) + self.status_msg_delim + "\n"
		map_rotation_text += _format_map_rotation("Арена", map_rotation_resp["arenas"]) + self.status_msg_delim + "\n"
		map_rotation_text += _format_map_rotation("Рангова арена", map_rotation_resp["arenasRanked"]) + "\n"

		map_rotation_text = map_rotation_text.strip()
		return map_rotation_text

	def get_realtime_status(self, realtime_stat):
		result_str = self.trans(realtime_stat["currentState"])

		if "selectedLegend" in realtime_stat:
			result_str += " на %s" % self.trans("on_" + realtime_stat["selectedLegend"])
		if "currentStateSecsAgo" in realtime_stat:
			result_str += " (%s)" % format_time(realtime_stat["currentStateSecsAgo"])
		return result_str

	def fetch_players_stats(self):
		#_minute = int((int(time.time()) % (60 * 60)) / 60)
		request_url = "https://api.mozambiquehe.re/bridge?version=5&platform=PC&player=%s&auth=%s" % (
			",".join(["Nephelim1337", "Nuffai", "Alptraumsong"]),
			#["Nephelim1337", "Nuffai", "Alptraumsong"][_minute % 3], # workaround to use less reqs/sec to work fine together with pathy daemon
			self.MOZAM_API_KEY
		)
		resp_raw = requests.get(request_url)
		try:
			resp = resp_raw.json()
		except Exception as e:
			print("Invalid mozam response: %s" % resp_raw.text)
			raise e

		try:
			self.validate_stats(resp)
		except Exception as e:
			print("Invalid mozam response (json structure is not ok): %s" % resp_raw.text)
			raise e

		return resp


	def validate_stats(self, stats):
		if type(stats) != list:
			stats = [stats]

		for player in stats:
			pass

	def marsian_to_ua(self, txt):
		replace_map = {
			"q": "й",
			"w": "ц",
			"e": "у",
			"r": "к",
			"t": "е",
			"y": "н",
			"u": "г",
			"i": "ш",
			"o": "щ",
			"p": "з",
			"[": "х",
			"]": "ї",
			"a": "ф",
			"s": "і",
			"d": "в",
			"f": "а",
			"g": "п",
			"h": "р",
			"j": "о",
			"k": "л",
			"l": "д",
			";": "ж",
			"'": "є",
			"z": "я",
			"x": "ч",
			"c": "с",
			"v": "м",
			"b": "и",
			"n": "т",
			"m": "ь",
			",": "б",
			".": "ю",
			"/": ".",
			"Q": "Й",
			"W": "Ц",
			"E": "У",
			"R": "К",
			"T": "Е",
			"Y": "Н",
			"U": "Г",
			"I": "Ш",
			"O": "Щ",
			"P": "З",
			"{": "Х",
			"}": "Ї",
			"A": "Ф",
			"S": "І",
			"D": "В",
			"F": "А",
			"G": "П",
			"H": "Р",
			"J": "О",
			"K": "Л",
			"L": "Д",
			":": "Ж",
			"\"": "Є",
			"Z": "Я",
			"X": "Ч",
			"C": "С",
			"V": "М",
			"B": "И",
			"N": "Т",
			"M": "Ь",
			"<": "Б",
			">": "Ю",
			"?": ",",
			"~": "₴",
			"@": "\"",
			"#": "№",
			"$": ";",
			"^": ":",
			"&": "?",
			"ы": "і",
			"э": "є",
			"ъ": "ї",
			"Ы": "І",
			"Э": "Є",
			"Ъ": "Ї"
		}
		return replace_char_map(txt, replace_map)

	def on_monday_cron(self):
		self.call_tg_api("sendPhoto", {"chat_id": self.TARG_CHAT_ID, "photo": self.MONDAY_IMG_ID, "parse_mode": "HTML", "disable_notification": True})
		#self.call_tg_api("sendPhoto", {"chat_id": self.DEBUG_CHAT_ID, "photo": self.MONDAY_IMG_ID, "parse_mode": "HTML", "disable_notification": True})

	def get_yt_chan_videos(self, channel_url):
		channel_page = requests.get(channel_url).text
		video_ids = re.findall("\"videoId\":\s*\"([^\"]+)\"", channel_page)

		result_videos = []
		for vid_id in video_ids:
			vid_url = "https://www.youtube.com/watch?v=%s" % vid_id
			if not vid_url in result_videos:
				result_videos.append(vid_url)

		return result_videos

	def on_yt_check(self):
		vids_to_notify = []
		vids = self.get_yt_chan_videos("https://www.youtube.com/c/playapex/videos")
		if not vids:
			raise Exception("Videos list is empty")

		for vid_url in vids:
			if not vid_url == self.state.get(["yt_news", "last_link"]):
				vids_to_notify.append(vid_url)
			else:
				break
		self.state.set(["yt_news", "last_link"], vids[0])

		vids_to_notify.reverse()
		vids_to_notify = vids_to_notify[-3:]
		for link in vids_to_notify:
			self.notify(link)

		self.state.save()

	def get_crafting_preview(self, preview_name):
		if not preview_name:
			return

		preview_path = self.cache_dir / (preview_name + ".png")
		if preview_path.exists():
			return preview_path
		else:
			return self.create_crafting_preview(preview_name)

	def create_crafting_preview(self, preview_name):
		def _resize_to_height(img, height):
			resize_ratio = height / img.height
			result_width  = int(img.width * resize_ratio)
			result_height = int(img.height * resize_ratio)
			return img.resize((result_width, result_height))

		preview_height = 100
		parts_margin = 2
		preview_parts = preview_name.split("_")

		parts = []
		preview_width = 0
		for part_name in preview_parts:
			part_path = self.cache_dir / part_name
			if not part_path.exists():
				print("Crafting preview not found: %s" % part_name)
				continue

			part_img = Image.open(part_path)
			part_img = _resize_to_height(part_img, preview_height)
			parts.append(part_img)
			preview_width += part_img.width

		if not parts:
			return
		preview_width += parts_margin * (len(parts) - 1)

		preview_img = Image.new("RGB", (preview_width, preview_height))
		paste_pointer = 0
		for part_img in parts:
			preview_img.paste(part_img, (paste_pointer, 0))
			paste_pointer += part_img.width + parts_margin

		preview_path = self.cache_dir / (preview_name + ".png")
		preview_img.save(preview_path)
		return preview_path


	def dl_file_through_tg(self, url, dest):
		sent_msg = self.call_tg_api("sendDocument", {"chat_id": self.dl_proxy_chat_id, "document": url, "caption": "Caching %s" % url})
		file_id = sent_msg["document"]["file_id"]

		tg_file = self.call_tg_api("getFile", {"file_id": file_id})
		tg_url = "https://api.telegram.org/file/bot%s/%s" % (self.BOT_TOKEN, tg_file["file_path"])

		req = requests.get(tg_url, allow_redirects=True)
		open(dest, 'wb').write(req.content)

	def get_cached_path(self, url: str):
		cache = self.state.get("cache")
		if cache:
			result_path = cache.get(url)
			if result_path:
				return Path(result_path)
		else:
			self.state.set("cache", {})

		file_name = get_rnd_str(16)
		file_dest = self.cache_dir / file_name
		self.dl_file_through_tg(url, file_dest)

		self.state.set(["cache", url], file_name)

		return file_dest

	def get_crafting_rotation(self):
		crafting_rotation_resp = requests.get("https://api.mozambiquehe.re/crafting?&auth=%s" % self.MOZAM_API_KEY).json()
		crafting_rotation_text = "<b>В реплікаторах зараз:</b>\n"

		now = int(time.time())
		img_urls = []
		for bundle in crafting_rotation_resp:
			if not "bundleContent" in bundle:
				continue
			if bundle["bundle"] in ["ammo", "evo", "health_pickup", "shield_pickup", "weapon_one", "weapon_two"]:
				continue

			for item in bundle["bundleContent"]:
				if not item["itemType"]:
					continue

				cost = item['cost']
				name = self.trans(item['itemType']['name'])
				if bundle.get("end"):
					seconds_left = bundle["end"] - now
					time_left = format_time(seconds_left)
				else:
					time_left = "∞"
				item_str = f"<b>[{cost}] {name}</b> <i>(буде ще {time_left})</i>"
				crafting_rotation_text += item_str + "\n"

				if item['itemType'].get("asset"):
					img_urls.append(item['itemType']["asset"])

		crafting_rotation_text = crafting_rotation_text.strip()

		img_names = []
		for img_url in img_urls:
			img_names.append(self.get_cached_path(img_url).name)
		crafting_preview_name = "_".join(img_names)
		preview_url = f"https://viva88.pythonanywhere.com/crafting_preview?icons={crafting_preview_name}"
		nbsp = "\u2060"
		preview_link = f"<a href=\"{preview_url}\">{nbsp}</a>"
		crafting_rotation_text += preview_link

		return crafting_rotation_text.strip()















