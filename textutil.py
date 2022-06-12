import random
import util
from util import log
from const import *

_cached_textdata = {}

def get_dict(dict_path):
	if not _cached_textdata.get(dict_path.name):
		with dict_path.open("r", encoding="utf-8") as fhandle:
			lines = fhandle.readlines()
		_cached_textdata[dict_path.name] = [s.strip() for s in lines]
	
	return _cached_textdata[dict_path.name]

def get_moniker(plural=False):
	is_doubled = util.chance(0.05)
	
	gr, adj_ending = _get_base_gr(plural=plural)
	adjectives = get_adjectives(ending=adj_ending)
	
	if is_doubled:
		suffix_gr, _ = _get_base_gr(plural=plural)
		gr = f"{gr}-{suffix_gr}"
	
	return f"{adjectives} {gr}"

def get_adjectives(ending=None, max_count=3):
	adjectives = get_dict(TEXT_ADJECTIVES_DICT)
	
	# randomly calculating the number of adjectives
	adj_count = 1
	for i in range(max_count-1):
		if not random.randint(0, 5):
			adj_count += 1
	
	result = []
	for _ in range(adj_count):
		adj = random.choice(adjectives)
		if ending:
			adj = adj[:-2] + ending
		result.append(adj)
	
	return " ".join(result)

# for repeating operations encapsulation purposes only
# returns rnd gr with prefix and ending for modifiers
def _get_base_gr(plural=False):
	prefixes = get_dict(TEXT_PREFIXES_DICT)
	
	if plural:
		grs_plur = get_dict(TEXT_GRS_PLUR_DICT)
	else:
		grs = get_dict(TEXT_GRS_DICT)
	
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

def get_goodnight_wish(player_name):
	wish = f"Гуд найт, {player_name}\n"
	wish += f"{get_adjectives(ending='их')} снів "
	wish += random.choice(["🥱", "🛌", "😴", "💤"])
	return wish

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
	"kills_season_13": "Кіли в сезоні 13",
	"wins_season_13": "Віни в сезоні 13",
	"wins": "Віни",
	"scout_of_action_targets_hit": "Хітів в челенджі \"Scout of action\"",
	"jackson_bow_out_damage_done": "Дамагу в челенджі \"Jackson bow out\"",
	"smoke_show_damage_done": "Дамагу в челенджі \"Smoke show\"",
	"_matches": "Матчі",
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

def trans(txt, default=None):
	if txt in translations:
		return translations[txt]
	else:
		return default or txt

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
	"Гуд лак, хев фан, ни слова по-русски..."
]

def get_wish():
	wish = default_wish
	if util.chance(0.2):
		wish = random.choice(easter_wishes)
	return wish

def marsian_to_ua(txt):
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
	return util.replace_char_map(txt, replace_map)

