# Player 2

> *Every hero needs someone to carry the stuff.*

Game jam entry. Theme: **two playable characters**. Engine: Python + Pygame.

## Concept
A top-down real-time **roguelike**. The **Knight** fights his way through a dungeon, one room at a time. He's brave, loud and has no plan: he charges the nearest monster with whatever is in his hands, and uses his item the moment it seems like a good idea.

You are the **Helper** (Player 2). You carry the **backpack**. During each fight you walk around with WASD, dig the next piece of gear out of the bag and hand it to him. The right tool turns a losing fight into an easy one. Clear the room, pick a reward, move on. One life per run.

You don't fight. You make sure he's holding the right thing at the right time.

## A run
1. **Pick a bag** (Satchel, Hauler or Pouch). Each starts with its own kit; the Knight always starts holding the Sword. Then **get ready** for room 1 (see step 5).
2. **8 rooms, then the boss.** Each room is one screen with a random arena and a random enemy mix for its stage.
3. **Before each fight** the room is frozen behind an overlay showing its enemies (picture, count and the gear that beats each one) and advice ("Armor: the Sword is weak. Pickaxe!"). Nothing moves until **SPACE**.
4. **The room is clear** when every enemy is dead. He rests (+5 HP) and keeps his tool. Gear still in the Helper's hands and his unused item go to the **back of the bag** (his item stays in hand only if the bag is full).
5. **Between rooms:** pick 1 of 3 gear for the bag, or after rooms 3 and 6, one of a priest's blessings. Change your mind freely: click a taken card to give it back, or another card to swap your pick for it. The next room's enemies are shown the same way, so you can get ready for it: pick any two slots, among the bag's slots and **the Knight's tool and item hands**, to swap them (tools only go in his tool hand, items only in his item hand).
6. **The run ends** if the Knight dies or the Helper dies. Back to bag select.

**Quitting a run:** ESC (or P, or clicking "ESC pause" on the side panel) pauses a fight, with **Resume** and **Quit run**. Between rooms, the Quit run button at the top left (or ESC) asks once more, then quits. Quitting goes back to the main menu.

## The Knight
- Targets the **nearest enemy**, walks to it (around walls) and swings on a cooldown (0.8 s).
- **Damage depends on his tool** and the enemy's tags (see Gear). Bare-handed he does 1.
- **Uses his item by himself** when the moment comes (see Gear).
- HP carries over between rooms (40 max).

## The Helper (you)
- **WASD** to move, **E** to act.
- **E, empty-handed:** dig out the **next entry in the bag's queue**. Digging takes the bag's extract time; you can't move while digging, and moving cancels it.
- **E, holding gear, next to the Knight:** hand it over. If that hand was full, the old gear goes to the **end of the queue**.
- **4 hearts.** Skulls hunt the Helper; every hit costs a heart (then a moment of safety) and knocks a dig back into the bag. If the Helper dies, the run is over.

## Backpacks
| Bag | Slots | Extract time | Starting kit |
|---|---|---|---|
| **Satchel** | 4 | 0.8 s | Potion, Key |
| **Hauler** | 6 | 1.6 s | 2 Potions, Key, 2 Bombs |
| **Pouch** | 2 | 0.3 s | Potion |

Bags start with items only; every other tool has to come from rewards.

The trade-off: a big bag carries the answer to everything but is slow to swap mid-fight; a small bag swaps instantly but you have to guess what's coming.

## Gear
**Tools (kept until replaced)**
| Gear | Damage | Special |
|---|---|---|
| Sword | 3 | ×0.34 vs armored (1 damage) |
| Pickaxe | 1 | ×5 vs armored |
| Torch | 1 | ×4 vs things that burn (skulls, vampires) |
| Shield | 1 | He takes half damage |

**Items (used up; he uses them by himself, except the Key)**
| Gear | When he uses it |
|---|---|
| Potion | Drinks it below 40% HP: +15 HP |
| Bomb | Throws it when 2+ enemies (or the boss) are close: 8 damage to each |
| Key | **The Helper's**, not his: dig it out and press E next to the chest to open it (two rewards after this room). E anywhere else puts it back at the end of the bag. It can't go in his hands |
| Poison | Final room only. He drinks it the moment he's handed it, and dies |

## Enemies
| Enemy | HP | Notes |
|---|---|---|
| Skeleton | 6 | Basic |
| Armored | 15 | Shrugs off the Sword. Bring the Pickaxe |
| Skull | 4 | Fast, **hunts the Helper**, burns |
| Vampire | 12 | Heals by half the damage it deals, burns |
| The Count (boss) | 50 | Big vampire, calls a Skull every 7 s. Torch him |

Enemy mixes are in `WAVES` in `game/run.py` (two options per room, picked at random); stats in `ENEMIES` in `game/enemies.py`; gear in `GEAR` in `game/gear.py`. All tuning lives in those tables.

## Blessings (priest rooms)
Prayer (heal 15), Bigger bag (+1 slot), Quick hands (dig 25% faster).

## The betrayal (ending)
Every room, the Knight takes the credit. When the Count falls, the Knight gloats ("Hah! My skill is unmatched."), and **Poison** appears on top of the bag. After a moment he heads for the exit.

- Hand him the Poison before he gets there: he drinks it without a second thought, and the ending plays: his last words ("Tell my mother... I was right..."), the Helper keeps the gold, the Knight gets the stale bread, "Player 2 wins."
- If he reaches the exit, he takes the gold and the credit again, and the run is over.

## Personality and humor
- He yells "TO GLORY!" when sent into a fight.
- On a boss kill: "Hah! My skill is unmatched."
- On death: a dramatic "Tell my mother... I was right..."
- The Helper never speaks.

## Arenas
Arenas are one screen (20×15 tiles, 320×240 px, shown at 960×720 with the HUD on the right). They're built by `tools/build_levels.py` from ASCII sketches, which autotiles the walls:

`#` wall, `.` floor, `K` Knight start, `H` Helper start, `X` exit door, `E` enemy spawn, `C` chest, plus symbols for decor (see the script's docstring). It writes Tiled maps (`levels/arena_*.tmj`) that can be polished in Tiled, but re-running the script overwrites them. The game loads every `.tmj` in `levels/`.

The Knight and the enemies find their way around pillars with a tile path search (`Level.route` in `game/level.py`), so arenas can have pillars and nooks, but keep every floor tile reachable.
