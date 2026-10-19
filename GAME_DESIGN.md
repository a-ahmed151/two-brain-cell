# Player 2

> *Every hero needs someone to carry the stuff.*

Game jam entry. Theme: **two playable characters**. Engine: Python + Pygame. Time: 2 days.

## Concept
A top-down real-time dungeon puzzle game. The **Knight** walks a fixed path through the dungeon and deals with whatever he runs into using the gear in his hands. He's brave, loud and has no plan. If he meets an obstacle without the right gear, he dies.

You are the **Helper** (Player 2). Before the round you see the whole dungeon, pack your backpack and set the order the Knight gets his gear in. During the run you walk around with WASD and hand him gear yourself when the plan needs fixing.

You don't fight. You make sure he's holding the right thing at the right time.

## The Knight
- Walks a **fixed path**, shown on the map during planning, at a constant speed
- Has **two hands**:
  - **Weapon/tool slot:** reusable, kept until replaced
  - **Item slot:** consumed when used
- **Uses gear automatically** when he reaches an obstacle that matches it (sword on a slime, key on a locked door)
- **Dies** if he reaches an obstacle and isn't holding the right gear
- Wins when he reaches the exit

## The Helper (you)
- Moves freely with **WASD**
- Carries the **backpack**, which holds a limited number of slots (e.g., 6, set per level)
- **Action button:** stand next to the Knight and press it to hand him the **next entry in the queue**. This is the only way gear changes hands, and you can't skip or reorder entries mid-run.
- **Swapping drops the old gear:** a new tool replaces his current one and the old tool falls on the floor. The same happens to an unused item. You can walk over it to pick it up again; it goes to the end of the queue.
- **Can die:** enemies and traps hurt the Helper too. If the Helper dies, the run fails.

## Core loop
1. **Preview:** see the full dungeon map, the Knight's path and every obstacle on it.
2. **Pack:** choose which gear from the level's available pool goes in the backpack. Slots are limited.
3. **Queue:** put the backpack contents in one ordered list.
4. **Run (real-time):** the Knight starts walking. You follow with WASD, staying close enough and alive, and press the action button at the right moments to hand him the next queue entry:
   - A tool goes into his tool slot (the old one drops to the floor)
   - An item goes into his item slot (an unused one drops to the floor)
5. **Result:** he reaches the exit and takes all the credit. If he dies, or you die, you're back at Pack with your choices kept.

The puzzle has two halves: **planning** (what to pack and in what order) and **execution** (being next to him at the right time without getting killed).

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
- **Backpack size:** fewer slots than obstacles, so tools have to be reused and items chosen carefully.
- **Order:** the Torch needs to be in hand before the dark room, but the Sword is needed for the slime inside it.
- **Timing:** obstacles close together leave little time between hand-offs. Hand off too early and he uses the wrong gear on the obstacle before.
- **Helper routing:** some hand-offs need the Helper to take a shortcut or get ahead of the Knight.
- **Helper danger:** traps and enemies near the path that the Knight handles easily but the Helper has to dodge.
- **Dropped gear:** an early tool can be picked back up and reused later in the level, saving a backpack slot.
- **Red herrings:** the available pool has gear the level doesn't need.

## Personality and humor
- The Knight yells "TO GLORY!" when the run starts.
- On success: "Hah! My skill is unmatched."
- On death: a dramatic "Tell my mother... I was right..."
- The Helper never speaks. They just sigh, and sweat drops appear.
- Level complete: the Knight gets 1,000 gold, the Helper gets "1 stale bread".

## Levels (each one screen)
1. **The Slime:** Sword only (tutorial: auto-use)
2. **Locked In:** Sword, then Key (tutorial: queue order)
3. **Cave-in:** Pickaxe vs Bomb choice with a small backpack
4. **Lights Out:** dark room with an enemy inside (Torch then Sword timing)
5. **Arrow Hall:** Shield, plus a manual hand-off right after
6. **The Gauntlet:** everything, with a tight backpack and a red herring

Levels 1–4 are the must-haves. 5–6 are stretch goals.

## Level format (Tiled)
Levels are built in [Tiled](https://www.mapeditor.org/) and exported as **JSON (`.tmj`)**. The game reads them with Python's built-in `json` module, so there's no extra dependency and nothing to break in the `pygbag` web build. Tilesets are saved **embedded** in the map so each level is one file.

**Tile layers**
| Layer | Contents |
|---|---|
| `floor` | Decorative ground tiles |
| `walls` | Solid tiles; the Helper can't walk through them |

**Object layers**
| Layer | Object | Notes |
|---|---|---|
| `path` | One **polyline** | The Knight's route, from first point to last |
| `objects` | `knight_start`, `helper_start`, `exit` | Point objects |
| `objects` | `slime`, `locked_door`, `pit`, `rock`, `cracked_wall`, `arrow_trap` | Obstacles on the path; set the Tiled **Class** field to the name |
| `objects` | `dark_room` | Rectangle; the area that needs the Torch |
| `objects` | `helper_hazard` | Something that hurts only the Helper (e.g., spike floor) |

**Map properties** (Map → Map Properties → custom properties)
| Property | Type | Example |
|---|---|---|
| `name` | string | `Locked In` |
| `backpack_size` | int | `4` |
| `gear_pool` | string | `sword,key,key,plank,bomb` |

**Rules for level designers**
- Tile size 32×32 (or 16×16, decided once for the whole game).
- Map size fits one screen, e.g. 20×15 tiles at 32 px.
- Draw the Knight's path through the obstacle objects; he handles an obstacle when he reaches it.
- Files go in `levels/`, named `01_the_slime.tmj`, `02_locked_in.tmj`, and so on; the number sets the order.

## Scope plan
**Day 1: core**
- Tiled `.tmj` loader (tile layers, path polyline, objects, map properties)
- Knight walks his path, auto-uses gear, dies or wins
- Helper WASD movement, action-button hand-off from the queue, dropped gear pickup
- Helper and Knight death → back to Pack
- Pack + queue screen (simple list UI)
- Gear: Sword, Pickaxe, Key, Plank
- Levels 1–3 with placeholder colored squares

**Day 2: content and polish**
- Torch, Shield, Bomb, Health Potion and their obstacles
- Levels 4–6, level select
- Speech bubbles, death and win animations, sounds, particles
- Title and ending screens, itch.io build (`pygbag`)

## Team split
- **Programmer 1:** map loader, Knight path movement, obstacles, auto-use and death
- **Programmer 2:** pack/queue screen, backpack, Helper movement and hand-off
- **Artist/designer:** 16×16 or 32×32 top-down pixel sprites and tilesets, levels in Tiled (puzzles are the content), dialogue

## Risks
- **Unclear rules:** show the Knight's held gear above his head and the next queue entry in the HUD, and highlight the Knight when you're in hand-off range.
- **Hand-offs feel fiddly:** use a generous hand-off range.
- **Too hard with both halves:** keep the early levels free of Helper danger, so players learn planning before execution.
- **Slow retries:** dying returns you to the Pack screen with everything kept, in under a second.
- **Over-scoping gear:** 8 pieces of gear max; 4 polished ones beat 8 rough ones.
