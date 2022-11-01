import random
import util
from util import log
from const import *

def get_moniker(noun_v_rod=False, noun_plur=False,
	adj_v_rod=False):
	is_doubled = util.chance(0.05)
	
	base, tags = _get_base_moniker(noun_v_rod, noun_plur)
	adj_ending = get_adj_ending(tags, v_rod=adj_v_rod)
	adjectives = get_adjectives(ending=adj_ending)
	
	if is_doubled:
		suffix, _ = _get_base_moniker(noun_v_rod, noun_plur)
		base = f"{base}-{suffix}"
	
	return f"{adjectives} {base}"

# for repeating operations encapsulation purposes only
# returns rnd noun with prefix and tags
def _get_base_moniker(v_rod=False, plur=False):
	is_prefixed = util.chance(0.15)
	prefix = get_dict_rnd(DICT_PREFIXES) if is_prefixed else ""
	noun, tags = get_noun(v_rod, plur)
	return (prefix + noun, tags)

def get_count_moniker(count):
	if count == 1:
		return f"Соло {get_moniker()}"
	adj_v_rod, adj_plur, noun_v_rod, noun_plur = get_count_props(count)
	moniker = get_moniker(noun_v_rod, noun_plur, adj_v_rod)
	return f"{count} {moniker}"

def get_noun(v_rod=False, plur=False):
	if not v_rod and not plur:
		noun_line = get_dict_rnd(DICT_NOUN_V_NAZ)
	elif v_rod and not plur:
		noun_line = get_dict_rnd(DICT_NOUN_V_ROD)
	if not v_rod and plur:
		noun_line = get_dict_rnd(DICT_NOUN_V_NAZ_PLUR)
	elif v_rod and plur:
		noun_line = get_dict_rnd(DICT_NOUN_V_ROD_PLUR)
	
	noun, tags = parse_tags(noun_line)
	if plur and not "p" in tags:
		tags.append("p")
	
	return (noun, tags)

def get_adj_ending(tags, v_rod=False):
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

def get_adjectives(ending=None, max_count=3):
	# randomly calculating the number of adjectives
	adj_count = 1
	for i in range(max_count-1):
		if util.chance(0.1):
			adj_count += 1
	
	result = []
	for _ in range(adj_count):
		adj = get_dict_rnd(DICT_ADJ)
		if ending:
			adj = adj[:-2] + ending
		result.append(adj)
	
	return " ".join(result)

goodnight_emoji = ["🥱", "🛌", "😴", "💤"]

def get_goodnight_wish(player_name):
	wish = f"Гуд найт, <b>{player_name}</b>\n"
	wish += f"<i>{get_adjectives(ending='их')} снів</i> "
	wish += random.choice(goodnight_emoji)
	return wish

def get_hokku():
	legends = ["Вруф", "Рейфа", "Рейф", "Рампа", "Валькірія", "Ватсон", "Лоба",
	"Бладхаунд", "Лайфа", "Лайфлайн", "Гіба", "Гібралтар", "Октан",
	"Патфайндер", "Хора", "Хорайзон", "Банга", "Ф'юз", "Аша", "Сір", "Міраж",
	"Каустік", "Рева", "Ревенант", "Кріпто", "Нюкасл"]
	
	lines = []
	for _ in range(3):
		line = get_dict_rnd(DICT_HOKKU)
		line = line.format(legend=random.choice(legends))
		lines.append(line)
	return "\n".join(lines)

_dict_cache = {}

def cache_rnd_prefetch(dict_path, size=50):
	dict_name = dict_path.stem
	lines_count = _dict_cache[dict_name]["lines_count"]
	prefetch = [random.randint(0, lines_count - 1) for _ in range(size)]
	_dict_cache[dict_name]["rnd_prefetch"] = prefetch
	
	with dict_path.open("r", encoding="utf-8") as dict_file:
		for i, line in enumerate(dict_file):
			if i not in prefetch:
				continue # optimization
			util.list_replace(prefetch, i, line.strip())

def get_dict_rnd(dict_path):
	dict_name = dict_path.stem
	
	if not dict_name in _dict_cache:
		_dict_cache[dict_name] = {
			# if last line is empty count lines produces number bigger by 1
			# than len(open(...).readlines()), so dicts must not have empty
			# lines
			"lines_count": util.count_lines(dict_path),
			"rnd_prefetch": []
		}
	if not _dict_cache[dict_name]["rnd_prefetch"]:
		cache_rnd_prefetch(dict_path)
	
	return _dict_cache[dict_name]["rnd_prefetch"].pop()

def parse_tags(line):
	word, *tags = line.split(":")
	return word, tags

def get_count_props(count):
	"""
	returns tuple of 4 boolean values representing
	adj v_rod, adj plur, noun v_rod, noun plur
	which should be applied to words multiplied by count
	"""
	count = abs(count)
	
	if count == 1:
		return False, False, False, False
	elif 2 <= count <= 4:
		return True, True, False, True
	else:
		return True, True, True, True

translations = {
	"Unranked": "Ніхто",
	"Rookie": "Нуб",
	"Bronze": "Бронза",
	"Silver": "Сільвер",
	"Gold": "Золото",
	"Platinum": "Платина",
	"Diamond": "Даймонд",
	"Master": "Мастер",
	"Apex Predator": "Предатор",
	"Unranked_v_rod": "Нікого",
	"Rookie_v_rod": "Нуба",
	"Bronze_v_rod": "Бронзу",
	"Silver_v_rod": "Сільвер",
	"Gold_v_rod": "Золото",
	"Platinum_v_rod": "Платину",
	"Diamond_v_rod": "Даймонд",
	"Master_v_rod": "Мастера",
	"Apex Predator_v_rod": "Предатора",
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
	"ultimate_damage": "Дамаг під ультою",
	"grapple_travel_distance": "Метри на граплі",
	"specialEvent_damage": "Дамаг",
	"kills_season_6": "Кіли в сезоні 6",
	"care_package_kills": "Кіли стволами з дропу",
	"smg_kills": "Кіли з пп",
	"grenades_distance": "Відстань гранат",
	"silenced_targets": "Засайленсяні вороги",
	"noxgassed_enemies_killed": "Загазовані кіли",
	"distance_on_stim": "Метрів під ЛСД",
	"wins_season_6": "Віни в сезоні 6",
	"wins_season_3": "Віни в сезоні 3",
	"arenas_wins": "Віни на аренах",
	"pinged_passive_loot": "Пінганутий лут",
	"wins_season_2": "Віни в сезоні 2",
	"special_arenas_kills": "Кіли на аренах",
	"ar_kills": "Кіли з вінтовок",
	"traps_destroyed": "Трапів знищено",
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
	"enemies_scanned": "Засканена здобич",
	"wins_season_8": "Віни в сезоні 8",
	"kills_season_1": "Кіли в сезоні 1",
	"doc_drone_healing": "Хп захілено дроном",
	"encore_execution_escaped": "Побіги під ультою",
	"grandsoiree_damage": "Дамаг",
	"ziplines_used_by_squad": "Використані зіпки тімейтами",
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
	"shield_damage": "Дамаг від ЕМІ",
	"passive_health_regen": "Відрегенено хп",
	"executions": "Фінішери",
	"ordnance_destroyed": "Збито рандомного дєрьма",
	"bamboozles": "Бамбузли",
	"marksman_kills": "Кіли з марксманів",
	"ultimate_allies_rescued": "Приземлення ультою на тімейтів",
	"kills_season_9": "Кіли в сезоні 9",
	"kills_season_11": "Кіли в сезоні 11",
	"wins_season_11": "Віни в сезоні 11",
	"kills_season_12": "Кіли в сезоні 12",
	"wins_season_12": "Віни в сезоні 12",
	"kills_season_13": "Кіли в сезоні 13",
	"wins_season_13": "Віни в сезоні 13",
	"kills_season_14": "Кіли в сезоні 14",
	"wins_season_14": "Віни в сезоні 14",
	"kills_season_15": "Кіли в сезоні 15",
	"wins_season_15": "Віни в сезоні 15",
	"kills_season_16": "Кіли в сезоні 16",
	"wins_season_16": "Віни в сезоні 16",
	"kills_season_17": "Кіли в сезоні 17",
	"wins_season_17": "Віни в сезоні 17",
	"kills_season_18": "Кіли в сезоні 18",
	"wins_season_18": "Віни в сезоні 18",
	"kills_season_19": "Кіли в сезоні 19",
	"wins_season_19": "Віни в сезоні 19",
	"kills_season_20": "Кіли в сезоні 20",
	"wins_season_20": "Віни в сезоні 20",
	"kills_season_21": "Кіли в сезоні 21",
	"wins_season_21": "Віни в сезоні 21",
	"kills_season_22": "Кіли в сезоні 22",
	"wins_season_22": "Віни в сезоні 22",
	"wins": "Віни",
	"scout_of_action_targets_hit": "Хітів в челенджі \"Scout of action\"",
	"jackson_bow_out_damage_done": "Дамагу в челенджі \"Jackson bow out\"",
	"smoke_show_damage_done": "Дамагу в челенджі \"Smoke show\"",
	"_matches": "Матчі",
	"Revenant_v_mis": "Реві ☠️",
	"Crypto_v_mis": "암호화 짜증 💻",
	"Horizon_v_mis": "Космобабі 🌠",
	"Gibraltar_v_mis": "наГібі 🐖",
	"Wattson_v_mis": "Багеті 🔌",
	"Fuse_v_mis": "Бабах-діду 🧨",
	"Bangalore_v_mis": "Бангі 🚬",
	"Wraith_v_mis": "Вруф 🥷🏻",
	"Octane_v_mis": "Наркомані 🤪",
	"Bloodhound_v_mis": "Собаці 🦮",
	"Caustic_v_mis": "Газовому діду 🤢",
	"Lifeline_v_mis": "Лайфі 🥁",
	"Pathfinder_v_mis": "Паті 🦾",
	"Loba_v_mis": "Лобстері 💋",
	"Mirage_v_mis": "Міражу 👯‍♂️",
	"Rampart_v_mis": "Рампі 🔧",
	"Valkyrie_v_mis": "Бідній нерфанутій нижче плінтуса Валькірії 🧚‍♀️",
	"Seer_v_mis": "Темному шляпері 👁",
	"Ash_v_mis": "Аші ⚔️",
	"Mad Maggie_v_mis": "Огонь-бабі 🔥",
	"Global_v_mis": "Всіх і зразу",
	"Newcastle_v_mis": "НьюКазлі 🛡",
	"Vantage_v_mis": "Вантажі 🦇",
	"Catalyst_v_mis": "Капіталіст 🔮",
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
	"inFiringRange": "На стрільбищі",
	"inRankedBrMatch": "В ранкед",
	"inRankedArMatch": "На ранкед аренах",
	"inPublicMatch": "В пабах",
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

def trans(txt, default=None):
	if default == None:
		default = txt
	return translations.get(txt, default)

default_wish = "Гуд лак, хев фан, донт дай! :)"
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
	"Гуд лак, хев фан, ни слова по-русски...",
	"<a href='https://youtu.be/dQw4w9WgXcQ'>" \
		"Гуд лак, хев фан, донт дай! :)</a>",
	"Uel kfr? [td afy? ljyn lfq ^)",
	"👍🍀,   🧲😄,   🙅‍♂️⚰️!",
	"Гуд лак, хев фан, ридай! 😭",
	"Bonus fortuna, habere fun, non moriatur! :)",
	"ጽቡቕ ዕድል፡ ተዘናግዑ ኣይትሞቱ! :)",
	"Гуд дай, донт фан.. Ні, там ж не так було...",
	"Нарешті!"
]

def get_wish():
	wish = default_wish
	if util.chance(0.2):
		wish = random.choice(easter_wishes)
	return wish

def fix_text_layout(txt):
	replace_maps = {
		"en": {
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
			"&": "?"
		},
		"ru": {
			"ы": "і",
			"э": "є",
			"ъ": "ї",
			"Ы": "І",
			"Э": "Є",
			"Ъ": "Ї"
		}
	}
	
	ru_characters = list(replace_maps["ru"].keys())
	contains_ru = any(char in txt for char in ru_characters)
	source_lang = "ru" if contains_ru else "en"
	
	return util.replace_char_map(txt, replace_maps[source_lang])

