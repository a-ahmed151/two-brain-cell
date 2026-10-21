# Player 2

> *Every hero needs someone to carry the stuff.*

Game jam entry. Theme: **two playable characters**. Engine: Python + Pygame.

## Concept
A top-down real-time **roguelike**. The **Knight** fights his way through a dungeon, one room at a time. He's brave, loud and has no plan: he charges the nearest monster with whatever is in his hands, and uses his item the moment it seems like a good idea.

You are the **Helper** (Player 2). You carry the **backpack**. During each fight you walk around with WASD, dig the next piece of gear out of the bag and hand it to him. The right tool turns a losing fight into an easy one. Clear the room, pick a reward, move on. One life per run.

You don't fight. You make sure he's holding the right thing at the right time.

## A run
0. **Levels** (main menu) lets you start a run at any room, the boss, or straight into the Trial: pick a door, pick a bag, and the run carries on from there with just the bag's starting kit. **Play** starts at room 1.
1. **Pick a bag** (Satchel, Hauler or Pouch). Each starts with its own kit; the Knight always starts holding the Sword. Then **get ready** for room 1 (see step 5). Before room 1, a short **intro** plays: the Knight barges into a room where the Helper is waiting, they "talk" (he talks; the Helper's replies are actions), and they walk out into room 1 together. ENTER moves the dialogue on; ESC or Skip skips it (`game/cutscene.py`).
2. **8 rooms, then the boss.** Each room is one screen with a random arena and a random enemy mix for its stage.
3. **Before each fight** the room is frozen behind an overlay showing its enemies (picture, count and the gear that beats each one) and advice ("Armor: the Sword is weak. Pickaxe!"). Nothing moves until **SPACE**.
4. **The room is clear** when every enemy is dead. Nothing moves you on automatically: the **exit door** in the top wall opens (an arrow points at it), and you still have time to open the chest. **Walk the Helper out of the exit** to move on. Once the room is clear the Knight tags along behind the Helper, and when the Helper reaches the door they walk out through it together. Each room also has an arched **entrance door**, closed behind you, showing where you came in. On leaving, he rests (+5 HP) and keeps his tool. Gear still in the Helper's hands and his unused item go to the **back of the bag** (his item stays in hand only if the bag is full).
5. **Between rooms:** pick 1 of 3 gear for the bag, or after rooms 3 and 6, one of a priest's blessings. Change your mind freely: click a taken card to give it back, or another card to swap your pick for it. The next room's enemies are shown the same way, so you can get ready for it: pick any two slots, among the bag's slots and **the Knight's tool and item hands**, to swap them (tools only go in his tool hand, items only in his item hand).
6. **The run ends** if the Knight dies or the Helper dies. Back to bag select.

**Quitting a run:** ESC (or P, or clicking "ESC pause" on the side panel) pauses a fight, with **Resume** and **Quit run**. Between rooms, the Quit run button at the top left (or ESC) asks once more, then quits. Quitting goes back to the main menu.

## The Knight
- Picks his target by **what he's holding**: the enemy his weapon does the most damage to (Pickaxe → Armored, Torch → Skulls and Vampires, Sword → anything but Armored), and among those, the nearest. With his fists or the Shield every enemy is the same to him, so he takes the nearest. He walks to it (around walls) and swings on a cooldown (0.8 s).
- **Damage depends on his tool** and the enemy's tags (see Gear). Bare-handed he does 1.
- **Uses his item by himself** when the moment comes (see Gear).
- HP carries over between rooms (40 max).

## The Helper (you)
- **WASD** to move, **E** to act.
- **E, empty-handed:** dig out the **next entry in the bag's queue**. Digging takes the bag's extract time; you can't move while digging, and moving cancels it.
- **E, holding gear, next to the Knight:** hand it over. If that hand was full, the old gear goes to the **end of the queue**.
- **4 hearts for the whole run.** They never come back: nothing heals the Helper, not between rooms, not at a shrine. Every hit costs a heart (then a moment of safety) and knocks a dig back into the bag. If the Helper dies, the run is over.
- **Don't get too close.** Skulls always hunt the Helper. Every other enemy goes for the Knight, but turns on the Helper who comes within 24 px ("!" over its head), and keeps chasing until the Helper is 56 px away ("?", back to the Knight). The Helper can't fight back; he's faster than every enemy, so **running away** is the only way to shake them. Hand gear over from behind the Knight, not from the middle of the fight.

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
| Sword | 3 | ×0.67 vs armored (2 damage) |
| Pickaxe | 1 | ×5 vs armored |
| Torch | 1 | ×4 vs things that burn (4 to skulls), and ×2 more vs vampires (8). Fire: a vampire it hits can't heal any more |
| Shield | 1 | He takes half damage |

**Items (used up; he uses them by himself, except the Key)**
| Gear | When he uses it |
|---|---|
| Potion | Drinks it below 40% HP: +15 HP |
| Bomb | Throws it as soon as any enemy is close: 8 damage to each enemy in range |
| Key | **The Helper's**, not his: dig it out and press E next to the chest to open it. The chest gives a random item (Potion, Bomb or Key) straight into the bag (it always fits, in the Key's slot). E anywhere else puts it back at the end of the bag. It can't go in his hands |
| Poison | Final room only. He drinks it the moment he's handed it, and dies |

## Enemies
| Enemy | HP | Notes |
|---|---|---|
| Skeleton | 6 | Basic |
| Armored | 15 | Shrugs off the Sword. Bring the Pickaxe |
| Skull | 4 | Fast, **hunts the Helper**, burns |
| Vampire | 12 | Heals by a third of the damage it deals (at least 1), until the Torch burns it |
| The Count (boss) | 50 | Big vampire, calls a Skull every 7 s. Torch him |

Enemy mixes are in `WAVES` in `game/run.py` (two options per room, picked at random); stats in `ENEMIES` in `game/enemies.py`; gear in `GEAR` in `game/gear.py`. All tuning lives in those tables.

## Blessings (priest rooms)
Prayer (heal 15), Bigger bag (+1 slot), Quick hands (dig 25% faster).

## The Trial (optional challenge)
On the way to room 8, once per run, **a sealed door** offers the Trial of the Four Seals (`game/trial.py`). Walk past for the normal reward, or go in.

- **The quiz is answered by doing.** Before going in you read four riddles and pack a lent **Trial Pack** (8 slots, your bag's dig speed): Pickaxe, Torch, 2 Bombs, Potion, Shield. His own hands come along; your bag waits outside and is given back afterwards.
- **Four seals, one after another**, in their own room (the Hall of Seals, `levels/trial.tmj`). Each seal's monsters are hurt by **one piece of gear only**; everything else shows "immune". The riddle of the next seal shows between seals.

| Seal | Riddle | Monsters | Only hurt by |
|---|---|---|---|
| I | They wear the mountain. Break it. | 3 Iron Wardens | Pickaxe |
| II | Born of dark, they fear the light. | 4 Shades, 2 Wisps (Wisps hunt the Helper) | Torch |
| III | Blades can't wake stone. Thunder can. | 4 Gargoyles, in pairs | Bomb |
| IV | Iron and shadow together. Be quick! | 2 Wardens, 2 Shades, 2 Wisps | Pickaxe *and* Torch: swap mid-fight |

- **Spike traps** rise and fall in two groups that take turns (the up-down lanes, then the rest). Raised spikes take a heart from the Helper and 1 HP from the Knight. The Shield is a red herring; the Potion is your only heal for him.
- He throws a Bomb as soon as any monster is near, so handing it over before seal III wastes it. If a seal needs gear that's used up (Bombs), the seal grants another, so it can never get stuck.
- **Win:** walk out together: he's **fully healed**, your bag gets **+1 slot**, and you pick **2 rewards**. **Lose:** the run is over, and hearts lost in there stay lost.

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

`#` wall, `.` floor, `K` Knight start, `H` Helper start, `NN` entrance door and `XX` exit door (two tiles wide, in the top wall, with floor below), `E` enemy spawn, `C` chest, plus symbols for decor (see the script's docstring). It writes Tiled maps (`levels/arena_*.tmj`) that can be polished in Tiled, but re-running the script overwrites them. The game loads every `.tmj` in `levels/`; `trial*.tmj` is the Trial's room and is never used for a normal room.

The Knight and the enemies find their way around pillars with a tile path search (`Level.route` in `game/level.py`), so arenas can have pillars and nooks, but keep every floor tile reachable.
