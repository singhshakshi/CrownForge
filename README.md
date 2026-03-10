# ⚔️ Crown Forge

Crown Forge is a fully featured Kingdom Life Simulation RPG that runs entirely inside Discord. Every server operates as its own independent kingdom with its own King, Queen, economy, laws and political hierarchy. Players build characters, rise through ranks, fight for the throne, steal from rivals, farm crops, trade on the marketplace and navigate a living medieval world — all through slash commands. Core character stats like level, HP, attack and defense carry across every server a player joins, while their role, rank, coins, bank balance and reputation remain completely independent per kingdom. One player can be a feared King on one server and a humble Commoner on another.

---

## 👑 The Kingdom

The throne of every kingdom is decided through blood and steel. When a server has no King, the bot automatically summons the top five Warriors by combined stats into a **Royal Tournament** — a single elimination bracket with full interactive turn-based duels. Each match features Attack, Special Attack and Forfeit options with critical hits and miss chances. If a match ends in a tie, a **Sudden Death** round begins with both warriors reset to half HP. If that ties again, a **Lightning Round** triggers with double damage, no special attacks and first hit wins. The last warrior standing is crowned King with a massive server-wide announcement, a 1000 coin reward and a permanent King Trophy on their profile.

Any Warrior whose total stats exceed the current King's can issue a formal **war declaration** using `/challengeking` at any time. The King receives a private challenge embed and has ten minutes to accept or decline. If he accepts, a full tournament-style duel begins immediately. If he declines or fails to respond, he is declared a coward, loses 500 coins and a new Royal Tournament is triggered automatically. A defeated challenger must wait 48 hours before challenging again.

The King can appoint a **Queen** through a royal proposal with accept and decline buttons, select elite **Kingsguard** members to serve as personal protectors and recruit **Royal Soldiers** to patrol and enforce the law. The King also controls the kingdom tax rate and distributes treasury funds at his discretion. On servers with only one or two players, a lone Warrior is crowned King by default — unopposed but legitimate.

---

## ⚔️ Roles

Every player chooses a role when they enter a kingdom. Each role comes with unique base stats, gender-specific pronouns and a distinct playstyle.

- **Warrior** — High HP, high defense, moderate attack. The only role eligible to become King and compete in Royal Tournaments.
- **Mage** — Low HP, low defense, devastating attack power. She specialises in powerful spells that can obliterate enemies in a single strike.
- **Queen** — Appointed by the King through a royal proposal. She receives bonus HP and magic attack stats along with a unique title and server-wide announcement.
- **Thief** — Balanced HP, solid crit chance. He excels at stealing coins from other players using the luck-based heist system.
- **Rival** — High attack, low defense. He is the King's sworn enemy with bonus damage against royalty and the ability to plot the King's downfall.
- **Worker** — High defense, steady income. They earn reliable coins through daily work actions and crafting.
- **Commoner** — Balanced across all stats. They start with no specialisation but can switch roles at level five.

---

## ⚖️ Law & Order

Crime in Crown Forge is a fully realised system with real consequences. The `/steal` command uses a **luck-based dice roll** from 1 to 100 — rolls 1 through 10 result in an epic fail with jail time and fines, 11 through 20 are close calls with nothing gained, and 21 through 100 are successful heists scaling from 8% up to 35% of the victim's wallet. A roll of 100 triggers a legendary heist that also steals a random inventory item. Victims have exactly **30 seconds** to use `/reporttheft` to catch the thief, which returns all stolen goods and jails the offender. False reports are tracked and penalised after three strikes.

Players can lock their wallets with `/lockwallet` to block all theft attempts entirely.

**Royal Lawyers** must pass a **bar exam** before they can practise. Once certified, they can defend jailed players in formal court cases where the King acts as judge. Each case is logged in public court records. Royal Soldiers patrol the kingdom and can arrest criminals on sight. Every crime is permanently recorded in a public **crime log** viewable by anyone, and the most wanted criminal is highlighted on the kingdom dashboard.

---

## 🌾 Economy & Life Sim

The economy runs on coins earned through quests, duels, farming, work and trade. Players can plant and harvest crops on **farm plots** with real-time growth timers and watering mechanics. The **bank** offers deposit accounts, locked savings with interest and loans with repayment deadlines.

A fully **player-driven marketplace** lets anyone list items for sale at custom prices. The King's tax rate is automatically applied to every transaction and deposited into the kingdom treasury. The **hospital** provides healing and debuff removal. Players collect and equip **pets** that boost combat stats and manage a full **inventory** of weapons, armour and consumables — all owned globally across servers but equipped independently per kingdom.

---

## 🎟️ Automated Events

Crown Forge runs five recurring events automatically with zero manual hosting required.

- **Lottery** — Triggers every 48 hours. Players buy tickets and a random winner takes the entire pot.
- **Treasure Hunt** — Once per week. A hidden treasure spawns and players race to find it for a large coin reward.
- **Seasonal Festival** — Every 5 days. Kingdom-wide celebration with bonus XP, boosted coin drops and special festival rewards.
- **Giveaway** — Every 24 hours. Random free items or coins distributed to active players.
- **Kingdom Throne Challenge** — Weekly event that opens a challenge window where any qualified Warrior can formally challenge the King for the crown.

All events are scheduled, announced and resolved by the bot automatically. The kingdom never sleeps.

---

## �️ Built With

- **Python 3.13** — Core language powering all bot logic and game systems.
- **discord.py** — Modern async library for Discord bot interaction, slash commands and interactive UI components.
- **SQLite + aiosqlite** — Lightweight async database handling all player data, kingdom state and event persistence.
- **python-dotenv** — Secure environment variable management for bot tokens and configuration.

---

## 📜 License

This project is **proprietary**. It is made publicly visible for portfolio and educational purposes only. Copying, redistributing, modifying or deploying this bot or any part of its codebase without explicit written permission from the author is strictly not permitted. All rights reserved.
