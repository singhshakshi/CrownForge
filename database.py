"""database.py — Global/server split architecture. players_global (stats) + players_server (role/coins)."""
import aiosqlite, os, json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "rpg_bot.db")

GLOBAL_FIELDS = {"username", "level", "xp", "hp", "max_hp", "attack", "defense", "crit_chance"}
SERVER_FIELDS = {"class", "coins", "mood"}

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
CREATE TABLE IF NOT EXISTS players_global (
    user_id INTEGER PRIMARY KEY, username TEXT,
    level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0,
    hp INTEGER, max_hp INTEGER, attack INTEGER, defense INTEGER,
    crit_chance REAL DEFAULT 0.0);
CREATE TABLE IF NOT EXISTS players_server (
    user_id INTEGER, guild_id INTEGER, class TEXT,
    coins INTEGER DEFAULT 100, mood TEXT DEFAULT 'neutral',
    PRIMARY KEY (user_id, guild_id));
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
    item_name TEXT, item_type TEXT, attack_bonus INTEGER DEFAULT 0,
    defense_bonus INTEGER DEFAULT 0, hp_bonus INTEGER DEFAULT 0, cost INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS equipped_items (
    user_id INTEGER, guild_id INTEGER, item_type TEXT, item_id INTEGER,
    PRIMARY KEY (user_id, guild_id, item_type));
CREATE TABLE IF NOT EXISTS player_pets (
    user_id INTEGER, pet_name TEXT, PRIMARY KEY (user_id, pet_name));
CREATE TABLE IF NOT EXISTS equipped_pet (
    user_id INTEGER, guild_id INTEGER, pet_name TEXT,
    PRIMARY KEY (user_id, guild_id));
CREATE TABLE IF NOT EXISTS hunt_trophies (
    user_id INTEGER, animal_name TEXT, count INTEGER DEFAULT 1,
    PRIMARY KEY (user_id, animal_name));
CREATE TABLE IF NOT EXISTS player_items (
    user_id INTEGER, item_name TEXT, item_type TEXT, quantity INTEGER DEFAULT 1,
    UNIQUE(user_id, item_name));
CREATE TABLE IF NOT EXISTS kingdom (
    guild_id INTEGER PRIMARY KEY, king_id INTEGER, queen_id INTEGER,
    tax_rate REAL DEFAULT 0, treasury INTEGER DEFAULT 0, last_event TEXT);
CREATE TABLE IF NOT EXISTS kingsguard (
    guild_id INTEGER, user_id INTEGER, PRIMARY KEY (guild_id, user_id));
CREATE TABLE IF NOT EXISTS royal_soldiers (
    guild_id INTEGER, user_id INTEGER, PRIMARY KEY (guild_id, user_id));
CREATE TABLE IF NOT EXISTS friends (
    user_id INTEGER, friend_id INTEGER, guild_id INTEGER,
    PRIMARY KEY (user_id, friend_id, guild_id));
CREATE TABLE IF NOT EXISTS friend_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT, from_user_id INTEGER,
    to_user_id INTEGER, guild_id INTEGER, status TEXT DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS farm_plots (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, guild_id INTEGER,
    crop TEXT, planted_at TEXT, watered INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS bank_accounts (
    user_id INTEGER, guild_id INTEGER, balance INTEGER DEFAULT 0,
    savings INTEGER DEFAULT 0, savings_locked_until TEXT, last_interest TEXT,
    PRIMARY KEY (user_id, guild_id));
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, guild_id INTEGER,
    amount INTEGER, borrowed_at TEXT, due_at TEXT, repaid INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS marketplace_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id INTEGER, guild_id INTEGER,
    seller_name TEXT, item_name TEXT, item_type TEXT,
    quantity INTEGER DEFAULT 1, price INTEGER, listed_at TEXT);
CREATE TABLE IF NOT EXISTS cooldowns (
    user_id INTEGER, guild_id INTEGER, action TEXT,
    last_used TEXT, PRIMARY KEY (user_id, guild_id, action));
CREATE TABLE IF NOT EXISTS active_buffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, guild_id INTEGER,
    buff_type TEXT, value INTEGER, expires_at TEXT);
CREATE TABLE IF NOT EXISTS kingdom_events (
    guild_id INTEGER PRIMARY KEY, started_at TEXT, ends_at TEXT);
CREATE TABLE IF NOT EXISTS rival_plots (
    user_id INTEGER, guild_id INTEGER, consecutive_plots INTEGER DEFAULT 0,
    last_plot TEXT, PRIMARY KEY (user_id, guild_id));
CREATE TABLE IF NOT EXISTS jail (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, guild_id INTEGER,
    crime TEXT, sentence_hours REAL, jailed_at TEXT, fine_amount INTEGER,
    bail_amount INTEGER, jailed_by INTEGER, released INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS crime_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, guild_id INTEGER,
    crime TEXT, timestamp TEXT, outcome TEXT);
CREATE TABLE IF NOT EXISTS lawyer_profiles (
    user_id INTEGER, guild_id INTEGER, passed_at TEXT,
    cases_won INTEGER DEFAULT 0, cases_lost INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1, PRIMARY KEY (user_id, guild_id));
CREATE TABLE IF NOT EXISTS bar_exam_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, guild_id INTEGER,
    attempted_at TEXT, score INTEGER, passed INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS court_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, prisoner_id INTEGER,
    lawyer_id INTEGER, crime TEXT, defense_text TEXT, outcome TEXT, timestamp TEXT);
CREATE TABLE IF NOT EXISTS steal_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, thief_id INTEGER,
    victim_id INTEGER, amount INTEGER, item_stolen TEXT, timestamp TEXT,
    reported INTEGER DEFAULT 0, reimbursed INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS report_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, reporter_id INTEGER,
    accused_id INTEGER, steal_timestamp TEXT, report_timestamp TEXT, outcome TEXT);
CREATE TABLE IF NOT EXISTS wallet_locks (
    user_id INTEGER, guild_id INTEGER, locked INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, guild_id));
CREATE TABLE IF NOT EXISTS leave_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, user_id INTEGER,
    username TEXT, role_at_leaving TEXT, level_at_leaving INTEGER,
    coins_at_leaving INTEGER, left_at TEXT);
CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER,
    status TEXT DEFAULT 'recruiting', participants TEXT, bracket TEXT,
    current_round INTEGER DEFAULT 0, winner_id INTEGER,
    started_at TEXT, ended_at TEXT);
CREATE TABLE IF NOT EXISTS lottery_rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER,
    ticket_price INTEGER DEFAULT 50, pot_total INTEGER DEFAULT 0,
    started_at TEXT, draw_at TEXT, winner_id INTEGER,
    rolled_over INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS lottery_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT, round_id INTEGER, guild_id INTEGER,
    user_id INTEGER, ticket_count INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS festivals (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER,
    festival_type TEXT, started_at TEXT, ends_at TEXT,
    active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS giveaway_rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER,
    prize_amount INTEGER, started_at TEXT, ends_at TEXT,
    winner_id INTEGER);
CREATE TABLE IF NOT EXISTS giveaway_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT, round_id INTEGER,
    guild_id INTEGER, user_id INTEGER,
    UNIQUE(round_id, user_id));
CREATE TABLE IF NOT EXISTS treasure_hunts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER,
    clue1 TEXT, answer1 TEXT, clue2 TEXT, answer2 TEXT,
    clue3 TEXT, answer3 TEXT, prize_amount INTEGER,
    started_at TEXT, current_stage INTEGER DEFAULT 1,
    active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS soldier_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, user_id INTEGER,
    pledge_text TEXT, applied_at TEXT,
    status TEXT DEFAULT 'pending');
        """)
        try: await db.execute("ALTER TABLE kingdom ADD COLUMN king_crowned_at TEXT")
        except: pass
        await db.commit()
    await _migrate_from_old_schema()

async def _migrate_from_old_schema():
    """Migrate old characters/inventory/pets tables to new global/server split."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if old characters table exists
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='characters'") as c:
            if not await c.fetchone():
                return  # No old data to migrate
        # Check if already migrated (players_global has data)
        async with db.execute("SELECT COUNT(*) FROM players_global") as c:
            if (await c.fetchone())[0] > 0:
                return  # Already migrated
        # Check if old table has data
        async with db.execute("SELECT COUNT(*) FROM characters") as c:
            if (await c.fetchone())[0] == 0:
                return  # Nothing to migrate
        print("  🔄  Migrating to global/server architecture...")
        # 1. characters → players_global (MAX stats per user)
        await db.execute("""INSERT OR IGNORE INTO players_global (user_id,username,level,xp,hp,max_hp,attack,defense,crit_chance)
            SELECT user_id, username, MAX(level), MAX(xp), MAX(hp), MAX(max_hp), MAX(attack), MAX(defense), MAX(crit_chance)
            FROM characters GROUP BY user_id""")
        # 2. characters → players_server
        await db.execute("""INSERT OR IGNORE INTO players_server (user_id,guild_id,class,coins,mood)
            SELECT user_id, guild_id, class, coins, mood FROM characters""")
        # 3. Migrate inventory (strip guild_id, keep items)
        try:
            async with db.execute("SELECT user_id, item_name, item_type, attack_bonus, defense_bonus, hp_bonus, cost FROM characters_old_inv_check LIMIT 0") as c: pass
        except: pass
        # Check if old inventory has guild_id column
        try:
            rows = []
            async with db.execute("SELECT id, user_id, guild_id, item_name, item_type, attack_bonus, defense_bonus, hp_bonus, cost, equipped FROM inventory WHERE 1=0") as c:
                pass  # Just checking schema
            # Old inventory has guild_id — migrate items to new format
            async with db.execute("SELECT DISTINCT user_id, item_name, item_type, attack_bonus, defense_bonus, hp_bonus, cost FROM inventory") as c:
                pass  # Items are already in new table format (no guild_id)
            # Migrate equipped status
            await db.execute("""INSERT OR IGNORE INTO equipped_items (user_id, guild_id, item_type, item_id)
                SELECT user_id, guild_id, item_type, id FROM inventory WHERE equipped=1""")
        except: pass
        # 4. Migrate pets
        try:
            await db.execute("""INSERT OR IGNORE INTO equipped_pet (user_id, guild_id, pet_name)
                SELECT user_id, guild_id, pet_name FROM player_pets WHERE equipped=1""")
        except: pass
        # 5. Merge hunt trophies across guilds
        try:
            await db.execute("""INSERT OR REPLACE INTO hunt_trophies (user_id, animal_name, count)
                SELECT user_id, animal_name, SUM(count) FROM hunt_trophies WHERE guild_id IS NOT NULL GROUP BY user_id, animal_name""")
        except: pass
        # 6. Merge player_items across guilds
        try:
            await db.execute("""INSERT OR REPLACE INTO player_items (user_id, item_name, item_type, quantity)
                SELECT user_id, item_name, item_type, SUM(quantity) FROM player_items WHERE guild_id IS NOT NULL GROUP BY user_id, item_name""")
        except: pass
        await db.commit()
        print("  ✅  Migration complete!")

# ═══ CHARACTERS (GLOBAL + SERVER) ═══
async def global_exists(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM players_global WHERE user_id=?", (uid,)) as c:
            return await c.fetchone() is not None

async def get_global_profile(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM players_global WHERE user_id=?", (uid,)) as c:
            r = await c.fetchone(); return dict(r) if r else None

async def create_character(uid, gid, username, cls, hp, atk, dfn, crit=0.0):
    async with aiosqlite.connect(DB_PATH) as db:
        has_global = False
        async with db.execute("SELECT 1 FROM players_global WHERE user_id=?", (uid,)) as c:
            has_global = await c.fetchone() is not None
        if not has_global:
            await db.execute("INSERT INTO players_global VALUES (?,?,1,0,?,?,?,?,?)",
                (uid, username, hp, hp, atk, dfn, crit))
        else:
            await db.execute("UPDATE players_global SET username=? WHERE user_id=?", (username, uid))
        await db.execute("INSERT OR REPLACE INTO players_server VALUES (?,?,?,100,'neutral')",
            (uid, gid, cls))
        await db.commit()

async def get_character(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT g.user_id, g.username, g.level, g.xp, g.hp, g.max_hp, g.attack, g.defense, g.crit_chance, "
            "s.class, s.coins, s.mood "
            "FROM players_global g JOIN players_server s ON g.user_id=s.user_id "
            "WHERE g.user_id=? AND s.guild_id=?", (uid, gid)) as c:
            r = await c.fetchone(); return dict(r) if r else None

async def character_exists(uid, gid): return await get_character(uid, gid) is not None

async def update_character(uid, gid, **kw):
    if not kw: return
    gkw = {k: v for k, v in kw.items() if k in GLOBAL_FIELDS}
    skw = {k: v for k, v in kw.items() if k in SERVER_FIELDS}
    async with aiosqlite.connect(DB_PATH) as db:
        if gkw:
            s = ", ".join(f"{k}=?" for k in gkw)
            await db.execute(f"UPDATE players_global SET {s} WHERE user_id=?", [*gkw.values(), uid])
        if skw:
            s = ", ".join(f"{k}=?" for k in skw)
            await db.execute(f"UPDATE players_server SET {s} WHERE user_id=? AND guild_id=?", [*skw.values(), uid, gid])
        await db.commit()

# ═══ LEVELING (GLOBAL) ═══
STAT_GROWTH = {"Warrior":{"hp":15,"attack":4,"defense":5},"Mage":{"hp":5,"attack":8,"defense":2},
    "Rogue":{"hp":10,"attack":5,"defense":3},"Thief":{"hp":10,"attack":5,"defense":3},
    "Worker":{"hp":12,"attack":2,"defense":4},"Rival":{"hp":10,"attack":6,"defense":3},
    "Commoner":{"hp":8,"attack":3,"defense":3}}

def xp_for_level(level): return int(100 * (level ** 1.5))

async def add_xp(uid, gid, amount):
    char = await get_character(uid, gid)
    if not char: return {"leveled_up": False}
    xp, lvl, up = char["xp"] + amount, char["level"], False
    while xp >= xp_for_level(lvl): xp -= xp_for_level(lvl); lvl += 1; up = True
    u = {"xp": xp, "level": lvl}
    if up:
        g = STAT_GROWTH.get(char["class"], STAT_GROWTH["Commoner"]); d = lvl - char["level"]
        u.update(max_hp=char["max_hp"]+d*g["hp"], attack=char["attack"]+d*g["attack"],
                 defense=char["defense"]+d*g["defense"])
        u["hp"] = u["max_hp"]
    await update_character(uid, gid, **u)
    return {"leveled_up": up, "new_level": lvl, "xp_needed": xp_for_level(lvl)}

async def add_coins(uid, gid, amount):
    char = await get_character(uid, gid)
    if not char: return
    if amount > 0:
        m = char.get("mood","neutral")
        if m == "happy": amount = int(amount * 1.1)
        elif m == "sad": amount = int(amount * 0.9)
    await update_character(uid, gid, coins=max(0, char["coins"] + amount))

# ═══ INVENTORY (GLOBAL ITEMS, PER-SERVER EQUIP) ═══
async def add_item_to_inventory(uid, gid, name, itype, atk_b, def_b, hp_b, cost):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO inventory(user_id,item_name,item_type,attack_bonus,defense_bonus,hp_bonus,cost) VALUES(?,?,?,?,?,?,?)",
            (uid, name, itype, atk_b, def_b, hp_b, cost)); await db.commit()

async def get_inventory(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM inventory WHERE user_id=?", (uid,)) as c:
            return [dict(r) for r in await c.fetchall()]

async def get_equipped_items(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT i.* FROM inventory i JOIN equipped_items e ON i.id=e.item_id "
            "WHERE e.user_id=? AND e.guild_id=?", (uid, gid)) as c:
            return [dict(r) for r in await c.fetchall()]

async def equip_item(uid, gid, name):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM inventory WHERE user_id=? AND item_name=?", (uid, name)) as c:
            item = await c.fetchone()
            if not item: return False; item = dict(item)
        # Unequip same type on this server
        await db.execute("DELETE FROM equipped_items WHERE user_id=? AND guild_id=? AND item_type=?",
            (uid, gid, item["item_type"]))
        # Equip new
        await db.execute("INSERT OR REPLACE INTO equipped_items VALUES(?,?,?,?)",
            (uid, gid, item["item_type"], item["id"]))
        await db.commit(); return True

async def has_item(uid, gid, name):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM inventory WHERE user_id=? AND item_name=?", (uid, name)) as c:
            return await c.fetchone() is not None

async def get_effective_stats(uid, gid):
    char = await get_character(uid, gid)
    if not char: return None
    eq = await get_equipped_items(uid, gid)
    ba = sum(i["attack_bonus"] for i in eq); bd = sum(i["defense_bonus"] for i in eq); bh = sum(i["hp_bonus"] for i in eq)
    pet = await get_equipped_pet(uid, gid)
    if pet:
        from cogs.pets import PETS_DATA
        pd = next((p for p in PETS_DATA if p["name"] == pet["pet_name"]), None)
        if pd: ba += pd["atk_boost"]; bd += pd["def_boost"]; bh += pd["hp_boost"]
    return {**char, "effective_attack": char["attack"]+ba, "effective_defense": char["defense"]+bd,
            "effective_max_hp": char["max_hp"]+bh, "bonus_atk": ba, "bonus_def": bd, "bonus_hp": bh}

# ═══ LEADERBOARD ═══
async def get_leaderboard(gid, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT g.*, s.class, s.coins, s.mood FROM players_global g "
            "JOIN players_server s ON g.user_id=s.user_id "
            "WHERE s.guild_id=? ORDER BY g.level DESC, g.xp DESC LIMIT ?", (gid, limit)) as c:
            return [dict(r) for r in await c.fetchall()]

# ═══ MOOD ═══
async def set_mood(uid, gid, mood): await update_character(uid, gid, mood=mood)

# ═══ KINGDOM ═══
async def get_kingdom(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM kingdom WHERE guild_id=?", (gid,)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def ensure_kingdom(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO kingdom(guild_id) VALUES(?)", (gid,)); await db.commit()
async def update_kingdom(gid, **kw):
    s = ", ".join(f"{k}=?" for k in kw)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE kingdom SET {s} WHERE guild_id=?", [*kw.values(), gid]); await db.commit()
async def get_strongest_warrior(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT g.*, s.class FROM players_global g JOIN players_server s ON g.user_id=s.user_id "
            "WHERE s.guild_id=? AND s.class='Warrior' ORDER BY (g.attack+g.defense+g.max_hp+g.level*10) DESC LIMIT 1", (gid,)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def add_kingsguard(gid, uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO kingsguard VALUES(?,?)", (gid, uid)); await db.commit()
async def remove_kingsguard(gid, uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM kingsguard WHERE guild_id=? AND user_id=?", (gid, uid)); await db.commit()
async def is_kingsguard(gid, uid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM kingsguard WHERE guild_id=? AND user_id=?", (gid, uid)) as c:
            return await c.fetchone() is not None
async def get_kingsguard_list(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT g.*, s.class FROM players_global g JOIN players_server s ON g.user_id=s.user_id "
            "JOIN kingsguard k ON g.user_id=k.user_id WHERE k.guild_id=? AND s.guild_id=?", (gid, gid)) as c:
            return [dict(r) for r in await c.fetchall()]
async def is_king(gid, uid):
    k = await get_kingdom(gid); return k and k["king_id"] == uid
async def is_queen(gid, uid):
    k = await get_kingdom(gid); return k and k["queen_id"] == uid

# ═══ ROYAL SOLDIERS ═══
async def add_royal_soldier(gid, uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO royal_soldiers VALUES(?,?)", (gid, uid)); await db.commit()
async def remove_royal_soldier(gid, uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM royal_soldiers WHERE guild_id=? AND user_id=?", (gid, uid)); await db.commit()
async def is_royal_soldier(gid, uid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM royal_soldiers WHERE guild_id=? AND user_id=?", (gid, uid)) as c:
            return await c.fetchone() is not None
async def get_royal_soldiers(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT g.*, s.class FROM players_global g JOIN players_server s ON g.user_id=s.user_id "
            "JOIN royal_soldiers rs ON g.user_id=rs.user_id WHERE rs.guild_id=? AND s.guild_id=?", (gid, gid)) as c:
            return [dict(r) for r in await c.fetchall()]

# ═══ COOLDOWNS ═══
async def get_cooldown(uid, gid, action):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT last_used FROM cooldowns WHERE user_id=? AND guild_id=? AND action=?", (uid, gid, action)) as c:
            r = await c.fetchone(); return datetime.fromisoformat(r[0]) if r else None
async def set_cooldown(uid, gid, action):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO cooldowns VALUES(?,?,?,?)", (uid, gid, action, datetime.utcnow().isoformat())); await db.commit()
def check_cooldown(last, secs):
    if not last: return True, 0
    elapsed = (datetime.utcnow() - last).total_seconds()
    return (True, 0) if elapsed >= secs else (False, int(secs - elapsed))

# ═══ PETS (GLOBAL OWN, PER-SERVER EQUIP) ═══
async def add_pet(uid, gid, name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO player_pets VALUES(?,?)", (uid, name)); await db.commit()
async def has_pet(uid, gid, name):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM player_pets WHERE user_id=? AND pet_name=?", (uid, name)) as c:
            return await c.fetchone() is not None
async def get_player_pets(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM player_pets WHERE user_id=?", (uid,)) as c:
            return [dict(r) for r in await c.fetchall()]
async def equip_pet_db(uid, gid, name):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM player_pets WHERE user_id=? AND pet_name=?", (uid, name)) as c:
            if not await c.fetchone(): return False
        await db.execute("INSERT OR REPLACE INTO equipped_pet VALUES(?,?,?)", (uid, gid, name))
        await db.commit(); return True
async def get_equipped_pet(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM equipped_pet WHERE user_id=? AND guild_id=?", (uid, gid)) as c:
            r = await c.fetchone(); return dict(r) if r else None

# ═══ FRIENDS (PER-SERVER) ═══
async def send_friend_request(fid, tid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM friends WHERE user_id=? AND friend_id=? AND guild_id=?", (fid,tid,gid)) as c:
            if await c.fetchone(): return "already_friends"
        async with db.execute("SELECT 1 FROM friend_requests WHERE from_user_id=? AND to_user_id=? AND guild_id=? AND status='pending'", (fid,tid,gid)) as c:
            if await c.fetchone(): return "already_sent"
        await db.execute("INSERT INTO friend_requests(from_user_id,to_user_id,guild_id) VALUES(?,?,?)", (fid,tid,gid)); await db.commit(); return "sent"
async def accept_friend_request(fid, tid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE friend_requests SET status='accepted' WHERE from_user_id=? AND to_user_id=? AND guild_id=? AND status='pending'", (fid,tid,gid))
        await db.execute("INSERT OR IGNORE INTO friends VALUES(?,?,?)", (fid,tid,gid))
        await db.execute("INSERT OR IGNORE INTO friends VALUES(?,?,?)", (tid,fid,gid)); await db.commit()
async def decline_friend_request(fid, tid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE friend_requests SET status='declined' WHERE from_user_id=? AND to_user_id=? AND guild_id=? AND status='pending'", (fid,tid,gid)); await db.commit()
async def get_friends(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT g.*, s.class, s.coins FROM players_global g "
            "JOIN players_server s ON g.user_id=s.user_id "
            "JOIN friends f ON g.user_id=f.friend_id "
            "WHERE f.user_id=? AND f.guild_id=? AND s.guild_id=?", (uid,gid,gid)) as c:
            return [dict(r) for r in await c.fetchall()]
async def remove_friend(uid, fid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM friends WHERE user_id=? AND friend_id=? AND guild_id=?", (uid,fid,gid))
        await db.execute("DELETE FROM friends WHERE user_id=? AND friend_id=? AND guild_id=?", (fid,uid,gid)); await db.commit()
async def are_friends(uid, fid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM friends WHERE user_id=? AND friend_id=? AND guild_id=?", (uid,fid,gid)) as c:
            return await c.fetchone() is not None

# ═══ FARMING (PER-SERVER) ═══
async def create_farm_plot(uid, gid, crop, planted_at):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO farm_plots(user_id,guild_id,crop,planted_at) VALUES(?,?,?,?)", (uid,gid,crop,planted_at)); await db.commit()
async def get_farm_plots(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM farm_plots WHERE user_id=? AND guild_id=?", (uid,gid)) as c:
            return [dict(r) for r in await c.fetchall()]
async def count_active_plots(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM farm_plots WHERE user_id=? AND guild_id=?", (uid,gid)) as c:
            return (await c.fetchone())[0]
async def water_plots(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE farm_plots SET watered=1 WHERE user_id=? AND guild_id=? AND watered=0", (uid,gid)); await db.commit()
async def remove_farm_plot(pid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM farm_plots WHERE id=?", (pid,)); await db.commit()

# ═══ BANK (PER-SERVER) ═══
async def get_bank_account(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bank_accounts WHERE user_id=? AND guild_id=?", (uid,gid)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def ensure_bank_account(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO bank_accounts(user_id,guild_id) VALUES(?,?)", (uid,gid)); await db.commit()
async def update_bank(uid, gid, **kw):
    s = ", ".join(f"{k}=?" for k in kw)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE bank_accounts SET {s} WHERE user_id=? AND guild_id=?", [*kw.values(),uid,gid]); await db.commit()
async def get_active_loan(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM loans WHERE user_id=? AND guild_id=? AND repaid=0 ORDER BY borrowed_at DESC LIMIT 1", (uid,gid)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def create_loan(uid, gid, amount, days=7):
    now = datetime.utcnow(); due = now + timedelta(days=days)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO loans(user_id,guild_id,amount,borrowed_at,due_at) VALUES(?,?,?,?,?)",
            (uid,gid,amount,now.isoformat(),due.isoformat())); await db.commit()
async def repay_loan(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE loans SET repaid=1 WHERE user_id=? AND guild_id=? AND repaid=0", (uid,gid)); await db.commit()

# ═══ MARKETPLACE (PER-SERVER) ═══
async def create_listing(sid, gid, sname, iname, itype, qty, price):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO marketplace_listings(seller_id,guild_id,seller_name,item_name,item_type,quantity,price,listed_at) VALUES(?,?,?,?,?,?,?,?)",
            (sid,gid,sname,iname,itype,qty,price,datetime.utcnow().isoformat())); await db.commit()
async def get_listings(gid, limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM marketplace_listings WHERE guild_id=? ORDER BY listed_at DESC LIMIT ?", (gid,limit)) as c:
            return [dict(r) for r in await c.fetchall()]
async def get_listing(lid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM marketplace_listings WHERE id=?", (lid,)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def remove_listing(lid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM marketplace_listings WHERE id=?", (lid,)); await db.commit()

# ═══ PLAYER ITEMS (GLOBAL) ═══
async def add_player_item(uid, gid, name, itype, qty=1):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT quantity FROM player_items WHERE user_id=? AND item_name=?", (uid, name)) as c:
            r = await c.fetchone()
        if r: await db.execute("UPDATE player_items SET quantity=quantity+? WHERE user_id=? AND item_name=?", (qty, uid, name))
        else: await db.execute("INSERT INTO player_items(user_id,item_name,item_type,quantity) VALUES(?,?,?,?)", (uid, name, itype, qty))
        await db.commit()
async def get_player_items(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM player_items WHERE user_id=?", (uid,)) as c:
            return [dict(r) for r in await c.fetchall()]
async def has_player_item(uid, gid, name, qty=1):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT quantity FROM player_items WHERE user_id=? AND item_name=?", (uid, name)) as c:
            r = await c.fetchone(); return r and r[0] >= qty
async def remove_player_item(uid, gid, name, qty=1):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT quantity FROM player_items WHERE user_id=? AND item_name=?", (uid, name)) as c:
            r = await c.fetchone()
        if not r: return False
        if r[0] <= qty: await db.execute("DELETE FROM player_items WHERE user_id=? AND item_name=?", (uid, name))
        else: await db.execute("UPDATE player_items SET quantity=quantity-? WHERE user_id=? AND item_name=?", (qty, uid, name))
        await db.commit(); return True

# ═══ BUFFS (PER-SERVER) ═══
async def add_buff(uid, gid, btype, val, hours):
    exp = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO active_buffs(user_id,guild_id,buff_type,value,expires_at) VALUES(?,?,?,?,?)", (uid,gid,btype,val,exp)); await db.commit()
async def get_active_buffs(uid, gid):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("DELETE FROM active_buffs WHERE expires_at<?", (now,)); await db.commit()
        async with db.execute("SELECT * FROM active_buffs WHERE user_id=? AND guild_id=? AND expires_at>?", (uid,gid,now)) as c:
            return [dict(r) for r in await c.fetchall()]
async def clear_debuffs(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM active_buffs WHERE user_id=? AND guild_id=? AND value<0", (uid,gid)); await db.commit()

# ═══ HUNT TROPHIES (GLOBAL) ═══
async def add_hunt_trophy(uid, gid, name):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT count FROM hunt_trophies WHERE user_id=? AND animal_name=?", (uid, name)) as c:
            r = await c.fetchone()
        if r: await db.execute("UPDATE hunt_trophies SET count=count+1 WHERE user_id=? AND animal_name=?", (uid, name))
        else: await db.execute("INSERT INTO hunt_trophies VALUES(?,?,1)", (uid, name))
        await db.commit()
async def get_hunt_trophies(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM hunt_trophies WHERE user_id=?", (uid,)) as c:
            return [dict(r) for r in await c.fetchall()]

# ═══ RIVAL PLOTS (PER-SERVER) ═══
async def get_rival_plots(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM rival_plots WHERE user_id=? AND guild_id=?", (uid,gid)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def increment_rival_plots(uid, gid):
    now = datetime.utcnow().isoformat(); ex = await get_rival_plots(uid, gid)
    async with aiosqlite.connect(DB_PATH) as db:
        if ex: await db.execute("UPDATE rival_plots SET consecutive_plots=consecutive_plots+1, last_plot=? WHERE user_id=? AND guild_id=?", (now,uid,gid))
        else: await db.execute("INSERT INTO rival_plots VALUES(?,?,1,?)", (uid,gid,now))
        await db.commit()
async def reset_rival_plots(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE rival_plots SET consecutive_plots=0 WHERE user_id=? AND guild_id=?", (uid,gid)); await db.commit()

# ═══ JAIL (PER-SERVER) ═══
async def jail_player(uid, gid, crime, hours, fine, bail, jailed_by=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO jail(user_id,guild_id,crime,sentence_hours,jailed_at,fine_amount,bail_amount,jailed_by) VALUES(?,?,?,?,?,?,?,?)",
            (uid,gid,crime,hours,datetime.utcnow().isoformat(),fine,bail,jailed_by))
        await db.execute("INSERT INTO crime_log(user_id,guild_id,crime,timestamp,outcome) VALUES(?,?,?,?,?)",
            (uid,gid,crime,datetime.utcnow().isoformat(),"jailed")); await db.commit()
async def get_active_jail(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jail WHERE user_id=? AND guild_id=? AND released=0 ORDER BY jailed_at DESC LIMIT 1", (uid,gid)) as c:
            r = await c.fetchone()
            if not r: return None; r = dict(r)
            jailed = datetime.fromisoformat(r["jailed_at"])
            if (datetime.utcnow() - jailed).total_seconds() >= r["sentence_hours"] * 3600:
                await db.execute("UPDATE jail SET released=1 WHERE id=?", (r["id"],)); await db.commit(); return None
            return r
async def release_prisoner(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE jail SET released=1 WHERE user_id=? AND guild_id=? AND released=0", (uid,gid)); await db.commit()
async def get_all_prisoners(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT j.*, g.username FROM jail j JOIN players_global g ON j.user_id=g.user_id "
            "WHERE j.guild_id=? AND j.released=0", (gid,)) as c:
            return [dict(r) for r in await c.fetchall()]
async def get_crime_log(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM crime_log WHERE user_id=? AND guild_id=? ORDER BY timestamp DESC", (uid,gid)) as c:
            return [dict(r) for r in await c.fetchall()]

# ═══ LAWYERS (PER-SERVER) ═══
async def get_lawyer(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM lawyer_profiles WHERE user_id=? AND guild_id=? AND active=1", (uid,gid)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def create_lawyer(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO lawyer_profiles(user_id,guild_id,passed_at,cases_won,cases_lost,active) VALUES(?,?,?,0,0,1)",
            (uid,gid,datetime.utcnow().isoformat())); await db.commit()
async def revoke_lawyer(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE lawyer_profiles SET active=0 WHERE user_id=? AND guild_id=?", (uid,gid)); await db.commit()
async def get_all_lawyers(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT l.*, g.username FROM lawyer_profiles l JOIN players_global g ON l.user_id=g.user_id "
            "WHERE l.guild_id=? AND l.active=1", (gid,)) as c:
            return [dict(r) for r in await c.fetchall()]
async def update_lawyer_record(uid, gid, won=True):
    col = "cases_won" if won else "cases_lost"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE lawyer_profiles SET {col}={col}+1 WHERE user_id=? AND guild_id=?", (uid,gid)); await db.commit()
async def add_bar_exam_attempt(uid, gid, score, passed):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO bar_exam_attempts(user_id,guild_id,attempted_at,score,passed) VALUES(?,?,?,?,?)",
            (uid,gid,datetime.utcnow().isoformat(),score,int(passed))); await db.commit()
async def get_last_bar_exam(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT attempted_at FROM bar_exam_attempts WHERE user_id=? AND guild_id=? ORDER BY attempted_at DESC LIMIT 1", (uid,gid)) as c:
            r = await c.fetchone(); return datetime.fromisoformat(r[0]) if r else None
async def add_court_record(gid, pid, lid, crime, defense, outcome):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO court_records(guild_id,prisoner_id,lawyer_id,crime,defense_text,outcome,timestamp) VALUES(?,?,?,?,?,?,?)",
            (gid,pid,lid,crime,defense,outcome,datetime.utcnow().isoformat())); await db.commit()
async def get_court_records(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM court_records WHERE guild_id=? ORDER BY timestamp DESC LIMIT 20", (gid,)) as c:
            return [dict(r) for r in await c.fetchall()]

# ═══ STEAL SYSTEM (PER-SERVER) ═══
async def log_steal(gid, thief_id, victim_id, amount, item_stolen=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO steal_log(guild_id,thief_id,victim_id,amount,item_stolen,timestamp) VALUES(?,?,?,?,?,?)",
            (gid, thief_id, victim_id, amount, item_stolen, datetime.utcnow().isoformat())); await db.commit()
async def get_recent_steal(gid, thief_id, victim_id, seconds=30):
    cutoff = (datetime.utcnow() - timedelta(seconds=seconds)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM steal_log WHERE guild_id=? AND thief_id=? AND victim_id=? AND timestamp>? AND reported=0 ORDER BY timestamp DESC LIMIT 1",
            (gid, thief_id, victim_id, cutoff)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def mark_steal_reported(steal_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE steal_log SET reported=1 WHERE id=?", (steal_id,)); await db.commit()
async def mark_steal_reimbursed(steal_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE steal_log SET reimbursed=1 WHERE id=?", (steal_id,)); await db.commit()
async def log_report(gid, reporter_id, accused_id, steal_ts, outcome):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO report_log(guild_id,reporter_id,accused_id,steal_timestamp,report_timestamp,outcome) VALUES(?,?,?,?,?,?)",
            (gid, reporter_id, accused_id, steal_ts, datetime.utcnow().isoformat(), outcome)); await db.commit()
async def count_false_reports(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM report_log WHERE guild_id=? AND reporter_id=? AND outcome='false'", (gid, uid)) as c:
            return (await c.fetchone())[0]
async def is_wallet_locked(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT locked FROM wallet_locks WHERE user_id=? AND guild_id=?", (uid, gid)) as c:
            r = await c.fetchone(); return r and r[0] == 1
async def set_wallet_lock(uid, gid, locked):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO wallet_locks VALUES(?,?,?)", (uid, gid, int(locked))); await db.commit()
async def get_random_inventory_item(uid, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM inventory WHERE user_id=? ORDER BY RANDOM() LIMIT 1", (uid,)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def remove_inventory_item_by_id(item_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM inventory WHERE id=?", (item_id,)); await db.commit()
async def transfer_inventory_item(item_id, new_uid, new_gid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE inventory SET user_id=? WHERE id=?", (new_uid, item_id)); await db.commit()

# ═══ LEAVE KINGDOM (SERVER WIPE ONLY) ═══
async def wipe_player_data(uid, gid):
    """Wipe per-server data. Global stats/items/pets persist."""
    async with aiosqlite.connect(DB_PATH) as db:
        for t in ["players_server","farm_plots","bank_accounts","cooldowns","active_buffs",
                  "rival_plots","jail","crime_log","lawyer_profiles","bar_exam_attempts",
                  "wallet_locks","loans","equipped_items","equipped_pet"]:
            await db.execute(f"DELETE FROM {t} WHERE user_id=? AND guild_id=?", (uid, gid))
        await db.execute("DELETE FROM friends WHERE (user_id=? OR friend_id=?) AND guild_id=?", (uid,uid,gid))
        await db.execute("DELETE FROM friend_requests WHERE (from_user_id=? OR to_user_id=?) AND guild_id=?", (uid,uid,gid))
        await db.execute("DELETE FROM marketplace_listings WHERE seller_id=? AND guild_id=?", (uid,gid))
        await db.execute("DELETE FROM kingsguard WHERE user_id=? AND guild_id=?", (uid,gid))
        await db.execute("DELETE FROM royal_soldiers WHERE user_id=? AND guild_id=?", (uid,gid))
        await db.execute("DELETE FROM steal_log WHERE (thief_id=? OR victim_id=?) AND guild_id=?", (uid,uid,gid))
        await db.execute("DELETE FROM report_log WHERE (reporter_id=? OR accused_id=?) AND guild_id=?", (uid,uid,gid))
        await db.execute("UPDATE kingdom SET king_id=NULL WHERE king_id=? AND guild_id=?", (uid,gid))
        await db.execute("UPDATE kingdom SET queen_id=NULL WHERE queen_id=? AND guild_id=?", (uid,gid))
        await db.commit()

async def log_leave(gid, uid, username, role, level, coins):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO leave_log(guild_id,user_id,username,role_at_leaving,level_at_leaving,coins_at_leaving,left_at) VALUES(?,?,?,?,?,?,?)",
            (gid, uid, username, role, level, coins, datetime.utcnow().isoformat())); await db.commit()
async def get_leave_log(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM leave_log WHERE guild_id=? ORDER BY left_at DESC", (gid,)) as c:
            return [dict(r) for r in await c.fetchall()]

# ═══ TOURNAMENTS ═══
async def create_tournament_record(gid, participants_json):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("INSERT INTO tournaments(guild_id,status,participants,started_at) VALUES(?,?,?,?)",
            (gid, 'recruiting', participants_json, datetime.utcnow().isoformat()))
        await db.commit(); return c.lastrowid
async def get_active_tournament(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tournaments WHERE guild_id=? AND status IN ('recruiting','active') ORDER BY started_at DESC LIMIT 1", (gid,)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def update_tournament_record(tid, **kw):
    s = ", ".join(f"{k}=?" for k in kw)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE tournaments SET {s} WHERE id=?", [*kw.values(), tid]); await db.commit()
async def get_tournament_history(gid, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tournaments WHERE guild_id=? AND status='completed' ORDER BY ended_at DESC LIMIT ?", (gid,limit)) as c:
            return [dict(r) for r in await c.fetchall()]
async def get_top_warriors(gid, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT g.*, s.class FROM players_global g JOIN players_server s ON g.user_id=s.user_id "
            "WHERE s.guild_id=? AND s.class='Warrior' ORDER BY (g.level*10+g.attack+g.defense+g.max_hp) DESC LIMIT ?", (gid,limit)) as c:
            return [dict(r) for r in await c.fetchall()]

# ═══ KINGDOM STATS ═══
async def get_total_players(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM players_server WHERE guild_id=?", (gid,)) as c:
            return (await c.fetchone())[0]
async def get_richest_player(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT g.username, s.coins FROM players_global g JOIN players_server s ON g.user_id=s.user_id "
            "WHERE s.guild_id=? ORDER BY s.coins DESC LIMIT 1", (gid,)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def get_most_wanted(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT g.username, g.user_id, COUNT(cl.id) as crime_count "
            "FROM crime_log cl JOIN players_global g ON cl.user_id=g.user_id "
            "WHERE cl.guild_id=? GROUP BY cl.user_id ORDER BY crime_count DESC LIMIT 1", (gid,)) as c:
            r = await c.fetchone(); return dict(r) if r else None

# ═══ LOTTERY ═══
async def create_lottery_round(gid, ticket_price=50, draw_at=None):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("INSERT INTO lottery_rounds(guild_id,ticket_price,started_at,draw_at) VALUES(?,?,?,?)",
            (gid, ticket_price, datetime.utcnow().isoformat(), draw_at))
        await db.commit(); return c.lastrowid
async def get_active_lottery(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM lottery_rounds WHERE guild_id=? AND winner_id IS NULL ORDER BY started_at DESC LIMIT 1", (gid,)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def buy_lottery_ticket(round_id, gid, uid, count=1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO lottery_tickets(round_id,guild_id,user_id,ticket_count) VALUES(?,?,?,?)",
            (round_id, gid, uid, count))
        await db.execute("UPDATE lottery_rounds SET pot_total=pot_total+? WHERE id=?",
            (count * 50, round_id))
        await db.commit()
async def get_lottery_tickets(round_id, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM lottery_tickets WHERE round_id=? AND guild_id=?", (round_id, gid)) as c:
            return [dict(r) for r in await c.fetchall()]
async def complete_lottery(round_id, winner_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE lottery_rounds SET winner_id=? WHERE id=?", (winner_id, round_id)); await db.commit()
async def get_lottery_history(gid, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM lottery_rounds WHERE guild_id=? AND winner_id IS NOT NULL ORDER BY draw_at DESC LIMIT ?", (gid, limit)) as c:
            return [dict(r) for r in await c.fetchall()]

# ═══ FESTIVALS ═══
async def create_festival(gid, festival_type, hours=24):
    now = datetime.utcnow(); ends = (now + timedelta(hours=hours)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE festivals SET active=0 WHERE guild_id=? AND active=1", (gid,))
        c = await db.execute("INSERT INTO festivals(guild_id,festival_type,started_at,ends_at) VALUES(?,?,?,?)",
            (gid, festival_type, now.isoformat(), ends))
        await db.commit(); return c.lastrowid
async def get_active_festival(gid):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM festivals WHERE guild_id=? AND active=1 AND ends_at>? ORDER BY started_at DESC LIMIT 1", (gid, now)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def end_festival(festival_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE festivals SET active=0 WHERE id=?", (festival_id,)); await db.commit()

# ═══ GIVEAWAYS ═══
async def create_giveaway(gid, prize_amount, hours=24):
    now = datetime.utcnow(); ends = (now + timedelta(hours=hours)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("INSERT INTO giveaway_rounds(guild_id,prize_amount,started_at,ends_at) VALUES(?,?,?,?)",
            (gid, prize_amount, now.isoformat(), ends))
        await db.commit(); return c.lastrowid
async def get_active_giveaway(gid):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM giveaway_rounds WHERE guild_id=? AND winner_id IS NULL AND ends_at>? ORDER BY started_at DESC LIMIT 1", (gid, now)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def enter_giveaway(round_id, gid, uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO giveaway_entries(round_id,guild_id,user_id) VALUES(?,?,?)",
            (round_id, gid, uid)); await db.commit()
async def get_giveaway_entries(round_id, gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM giveaway_entries WHERE round_id=? AND guild_id=?", (round_id, gid)) as c:
            return [dict(r) for r in await c.fetchall()]
async def complete_giveaway(round_id, winner_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE giveaway_rounds SET winner_id=? WHERE id=?", (winner_id, round_id)); await db.commit()

# ═══ TREASURE HUNTS ═══
async def create_treasure_hunt(gid, clue1, answer1, clue2, answer2, clue3, answer3, prize):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE treasure_hunts SET active=0 WHERE guild_id=? AND active=1", (gid,))
        c = await db.execute("INSERT INTO treasure_hunts(guild_id,clue1,answer1,clue2,answer2,clue3,answer3,prize_amount,started_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (gid, clue1, answer1, clue2, answer2, clue3, answer3, prize, datetime.utcnow().isoformat()))
        await db.commit(); return c.lastrowid
async def get_active_treasure_hunt(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM treasure_hunts WHERE guild_id=? AND active=1 ORDER BY started_at DESC LIMIT 1", (gid,)) as c:
            r = await c.fetchone(); return dict(r) if r else None
async def advance_treasure_hunt(hunt_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE treasure_hunts SET current_stage=current_stage+1 WHERE id=?", (hunt_id,)); await db.commit()
async def end_treasure_hunt(hunt_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE treasure_hunts SET active=0 WHERE id=?", (hunt_id,)); await db.commit()

# ═══ SOLDIER APPLICATIONS ═══
async def create_soldier_application(gid, uid, pledge_text):
    async with aiosqlite.connect(DB_PATH) as db:
        c = await db.execute("INSERT INTO soldier_applications(guild_id,user_id,pledge_text,applied_at) VALUES(?,?,?,?)",
            (gid, uid, pledge_text, datetime.utcnow().isoformat()))
        await db.commit(); return c.lastrowid
async def get_pending_applications(gid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT sa.*, g.username FROM soldier_applications sa "
            "JOIN players_global g ON sa.user_id=g.user_id "
            "WHERE sa.guild_id=? AND sa.status='pending' ORDER BY sa.applied_at ASC", (gid,)) as c:
            return [dict(r) for r in await c.fetchall()]
async def update_application_status(app_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE soldier_applications SET status=? WHERE id=?", (status, app_id)); await db.commit()
async def get_user_application(gid, uid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM soldier_applications WHERE guild_id=? AND user_id=? AND status='pending' LIMIT 1", (gid, uid)) as c:
            r = await c.fetchone(); return dict(r) if r else None
