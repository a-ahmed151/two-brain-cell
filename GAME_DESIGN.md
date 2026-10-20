# Player 2

> *Every hero needs someone to carry the stuff.*

Game jam entry. Theme: **two playable characters**. Engine: Python + Pygame. Time: 2 days.

## Concept
A top-down real-time dungeon puzzle game. The **Knight** walks a fixed path through the dungeon and deals with whatever he runs into using the gear in his hands. He's brave, loud and has no plan. If he meets an obstacle without the right gear, he dies.

You are the **Helper** (Player 2). Before the round you see the whole dungeon, **pick a backpack**, pack it and set the order the Knight gets his gear in. During the run you walk around with WASD and dig each piece of gear out of the bag and hand it to him in time.

You don't fight. You make sure he's holding the right thing at the right time.

**The core challenge is inventory management.** Every bag trades space for speed: a big bag carries everything but is slow to dig through, a small bag is fast but barely holds anything. Picking the right bag, the right gear and the right order is the puzzle, and each level is built so a different bag fits best.

## The Knight
- Walks a **fixed path**, shown on the map during planning, at a constant speed
- Has **two hands**:
  - **Weapon/tool slot:** reusable, kept until replaced
  - **Item slot:** consumed when used
- **Uses gear automatically** when he reaches an obstacle that matches it (sword on a slime, key on a locked door)
- **Dies** if he reaches an obstacle and isn't holding the right gear
- **Starts holding gear** in both hands (set per level, e.g. Sword and Key). This gear isn't in the backpack.
- Wins when he reaches the exit

## The Helper (you)
- Moves freely with **WASD**
- Carries **one backpack**, chosen before the run (see Backpacks). Its size limits how much gear you bring.
- **Action button, step 1: dig.** Empty-handed, press it **anywhere** to start digging out the **next entry in the queue**. You can't skip or reorder entries mid-run.
- **Digging takes time** (the bag's extract time). While digging you **can't move**, and a progress ring shows over the bag. When it fills, the gear is in the Helper's hands (shown above their head).
- **Moving cancels the dig.** The gear stays in the bag; you have to start over.
- **Action button, step 2: hand over.** Holding gear, stand next to the Knight and press it again to give it to him instantly. This is the only way gear changes hands. The Knight is highlighted when you're holding gear and in range.
- **One piece at a time:** you can't dig while your hands are full, so you can only ever be one hand-off ahead.
- **Swapping returns the old gear to the bag:** a new tool replaces his current one and the old tool goes to the **end of the queue**. The same happens to an unused item. It always fits, because the gear you just handed over freed its slot.
- **Can die:** enemies and traps hurt the Helper too, and you're a sitting duck while digging. If the Helper dies, the run fails.

## Backpacks
| Bag | Slots | Extract time | Unlocked |
|---|---|---|---|
| **Satchel** (normal) | 4 | 0.8 s | From the start |
| **Hauler** (big) | 6 | 1.6 s | Level 3 |
| **Pouch** (small) | 2 | 0.3 s | Level 4 |

Numbers are starting points for tuning. With the Knight at 30 px/s (about 2 tiles/s), he walks about 1.5 tiles during a Satchel dig, 3 tiles during a Hauler dig and half a tile during a Pouch dig.

Because you can dig ahead of time, extract speed matters most **right after a hand-off**: the next piece has to be dug out (standing still) before the next obstacle, while you also keep up with the Knight.

**What each bag is for**
- **Satchel:** the all-rounder. Enough room and speed for the tutorial levels, and a safe fallback later.
- **Hauler:** levels with many obstacles spread far apart. You can bring everything, but after each hand-off you lose ground standing still to dig out the next piece, and two obstacles close together can't both be covered in time.
- **Pouch:** levels with obstacles packed close together. Only two pieces of gear fit, so you win by cycling gear: hand him a tool, get his old one back at the end of the queue, and swap again. Reusable tools beat one-use items.

**Bag rules**
- You pick the bag on the Pack screen, before choosing gear. Switching bags empties it.
- All unlocked bags are offered on every level. Levels don't force a bag, they're designed so one fits best; a clever player can sometimes beat a level with the "wrong" one.
- A level that introduces a bag shows a short unlock card ("New bag: Hauler. Holds 6, slow to dig.") and has the matching puzzle.

## Core loop
1. **Preview:** see the full dungeon map, the Knight's path and every obstacle on it.
2. **Pick a bag:** choose from the unlocked backpacks. Space vs extract speed.
3. **Pack:** choose which gear from the level's available pool goes in the bag. Slots are limited by the bag.
4. **Queue:** put the bag contents in one ordered list.
5. **Run (real-time):** the Knight starts walking. You follow with WASD, staying alive, digging out the next queue entry whenever your hands are free, and catching up to hand it over before he needs it:
   - A tool goes into his tool slot (the old one goes back to the end of the queue)
   - An item goes into his item slot (an unused one goes back to the end of the queue)
6. **Result:** he reaches the exit and takes all the credit. If he dies, or you die, you're back at Pack with your bag and choices kept.

The puzzle has two halves: **planning** (which bag, what to pack and in what order) and **execution** (digging at the right moment, in a safe spot, and catching up to hand it over without getting killed).

## Gear

**Weapons/tools (reusable)**
| Gear | Handles |
|---|---|
| Sword | Enemies (slimes, skeletons) |
| Pickaxe | Rock piles, cracked walls |
| Torch | Dark rooms (without it, he walks into a hidden pit) |
| Shield | Arrow traps |

**Items (consumed on use)**
| Gear | Handles |
|---|---|
| Key | One locked door |
| Plank | One pit |
| Bomb | Cracked wall or a group of enemies |
| Health Potion | Saves him once from a lethal hit |

Overlap is intentional: a cracked wall can take the Pickaxe (reusable, but uses up the tool slot) or a Bomb (frees the tool slot, but costs a backpack slot).

## Puzzle design levers
- **Bag choice:** the main lever. Count the obstacles and measure the gaps between them: many obstacles far apart points to the Hauler, few obstacles close together points to the Pouch.
- **Backpack size:** fewer slots than obstacles, so tools have to be reused and items chosen carefully.
- **Order:** the Torch needs to be in hand before the dark room, but the Sword is needed for the slime inside it.
- **Timing:** obstacles close together leave little time between hand-offs, and a slow bag may not finish the next dig in the gap. Hand off too early and he uses the wrong gear on the obstacle before.
- **Dig spots:** the Helper needs a safe place to stand still and dig, then a route to catch up with the Knight. Put hazards where the obvious dig spot would be, or make the catch-up route long.
- **Helper routing:** some hand-offs need the Helper to take a shortcut or get ahead of the Knight.
- **Helper danger:** traps and enemies near the path that the Knight handles easily but the Helper has to dodge.
- **Returned gear:** swapped-out gear goes to the back of the queue, so a tool used early comes round again later. Plan the order so it comes back up when it's needed; the Knight's starting gear joins the rotation the first time it's swapped out.
- **Red herrings:** the available pool has gear the level doesn't need.

## Personality and humor
- The Knight yells "TO GLORY!" when the run starts.
- On success: "Hah! My skill is unmatched."
- On death: a dramatic "Tell my mother... I was right..."
- The Helper never speaks. They just sigh, and sweat drops appear.
- Level complete: the Knight gets 1,000 gold, the Helper gets "1 stale bread".

## Levels (each one screen)
| # | Level | Best bag | Teaches |
|---|---|---|---|
| 1 | **The Slime** | Satchel (only bag) | Auto-use, and digging gear out before he needs it |
| 2 | **Locked In** | Satchel (only bag) | Queue order: Sword, then Key |
| 3 | **The Long Hall** | Hauler (unlocked here) | Five or six obstacles spaced far apart; the Satchel can't fit them all. Dig after every hand-off and catch up. |
| 4 | **Cave-in** | Pouch (unlocked here) | Rocks and slimes packed tight; only a fast dig makes the gaps. Pickaxe over Bomb, and cycle the Sword back in. |
| 5 | **Lights Out** | Satchel or Pouch | Dark room with an enemy inside: Torch, then Sword right after |
| 6 | **The Gauntlet** | Player's choice | A long, spread-out first half and a tight cluster at the end. No bag is perfect; plan around its weakness. Red herrings in the pool. |

Levels 1–4 are the must-haves (they introduce all three bags). 5–6 are stretch goals. An **Arrow Hall** level (Shield, plus a hand-off right after) is a further stretch.

Levels 1–4 are the must-haves. 5–6 are stretch goals.

## Level format (Tiled)
Levels are built in [Tiled](https://www.mapeditor.org/) and exported as **JSON (`.tmj`)**. The game reads them with Python's built-in `json` module, so there's no extra dependency and nothing to break in the `pygbag` web build. Tilesets are saved **embedded** in the map so each level is one file.

**Tileset:** `assets/character and tileset/Dungeon_Tileset.png` (16×16 tiles, 10×10 grid). Add it in Tiled with tile size 16×16, margin 0, spacing 0, and tick **Embed in map**. The game draws the world at native size and scales the window up 3×.

**Tile layers**
| Layer | Contents |
|---|---|
| `floor` | Decorative ground tiles |
| `walls` | Solid tiles; the Helper can't walk through them |

**Object layers**
| Layer | Object | Notes |
|---|---|---|
| `path` | One **polyline** | The Knight's route, from first point to last |
| `objects` | `helper_start`, `exit` | Point objects (the Knight starts at the first point of his path) |
| `objects` | `slime`, `locked_door`, `pit`, `rock`, `cracked_wall`, `arrow_trap` | Obstacles on the path; set the Tiled **Class** field to the name |
| `objects` | `dark_room` | Rectangle; the area that needs the Torch |
| `objects` | `helper_hazard` | Something that hurts only the Helper (e.g., spike floor) |

**Map properties** (Map → Map Properties → custom properties)
| Property | Type | Example |
|---|---|---|
| `name` | string | `Locked In` |
| `unlocks_bag` | string | `hauler` (optional; bag unlocked when this level starts) |
| `gear_pool` | string | `sword,key,key,plank,bomb` |
| `knight_gear` | string | `sword,key` (what the Knight starts holding; one tool and/or one item) |

Bag stats live in code, not in maps, so they can be tuned in one place.

**Rules for level designers**
- Tile size 16×16, to match the art.
- Map size fits one screen: 20×15 tiles (320×240 px, shown at 960×720).
- Draw the Knight's path through the obstacle objects; he handles an obstacle when he reaches it.
- Files go in `levels/`, named `01_the_slime.tmj`, `02_locked_in.tmj`, and so on; the number sets the order.

## Scope plan
**Day 1: core**
- Tiled `.tmj` loader (tile layers, path polyline, objects, map properties)
- Knight walks his path, auto-uses gear, dies or wins
- Helper WASD movement, action-button dig (anywhere) and hand-off (next to the Knight), swapped gear back to the queue
- Three backpacks (slots + extract time), dig progress ring, unlock on level start
- Helper and Knight death → back to Pack
- Bag + pack + queue screen (simple list UI)
- Gear: Sword, Pickaxe, Key, Plank
- Levels 1–4 with placeholder colored squares

**Day 2: content and polish**
- Torch, Shield, Bomb, Health Potion and their obstacles
- Levels 5–6, level select, bag unlock cards
- A distinct sprite per bag (and a slower/faster dig animation)
- Speech bubbles, death and win animations, sounds, particles
- Title and ending screens, itch.io build (`pygbag`)

## Team split
- **Programmer 1:** map loader, Knight path movement, obstacles, auto-use and death
- **Programmer 2:** bag/pack/queue screen, backpacks and digging, Helper movement and hand-off
- **Artist/designer:** 16×16 top-down pixel sprites and tilesets, levels in Tiled (puzzles are the content), dialogue

## Risks
- **Unclear rules:** show the Knight's held gear above his head and the next queue entry in the HUD, show the gear the Helper is holding, and highlight the Knight when you can hand it over.
- **Hand-offs feel fiddly:** use a generous hand-off range.
- **Bag choice feels arbitrary:** on the Pack screen, show each bag's slots and extract time, and during planning show how far the Knight walks during one dig with the selected bag (a short bar along his path).
- **One bag dominates:** if playtesters always pick the same bag, tune slots and extract times before adding more levels.
- **Too hard with both halves:** keep the early levels free of Helper danger, so players learn planning before execution.
- **Slow retries:** dying returns you to the Pack screen with everything kept, in under a second.
- **Over-scoping gear:** 8 pieces of gear max; 4 polished ones beat 8 rough ones.
