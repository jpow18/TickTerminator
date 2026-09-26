# Flight guide

How to fly a survey that TickTerminator can use.

## 1. Select the time

Each pest is visible from the air only for part of the year. The months are for the northern hemisphere and change with the region and the weather.

| Pest | What to look for | When |
|---|---|---|
| Eastern tent caterpillar | Silk tents in the forks of branches, mostly on wild cherry and apple trees | Spring, from the time the leaves open (about March to May). Young tents are small (about 10 cm), and they grow larger each week. |
| Fall webworm | Silk webs that cover the leaves at the ends of branches | Late summer and fall (about July to October) |
| Bagworm | Brown, cone-shaped bags on evergreen trees | Late summer to winter |
| Pine processionary moth | White silk nests at the tips of pine branches | Winter (about December to March) |
| Defoliation | Trees with no leaves among green trees | Early summer, when the caterpillars eat |

Fly when the light is even: an overcast day, or the morning. Strong sun makes dark shadows and bright spots that the detector can confuse with nests. Do not fly in wind, because moving branches make blurred photos.

## 2. Select the height

Use `tickterminator plan` with the smallest target that you must find:

```bash
tickterminator plan --target-cm 10 --camera dji_mini_4_pro
```

```
Camera: DJI Mini 4 Pro (12 MP) (24 mm, 4032 x 3024 pixels)
Fly at most 28 m above the tree tops.
Ground resolution: 1.00 cm per pixel. A 10 cm target is 10 pixels wide.
Each photo covers 40 x 30 m.
With 80% overlap: take a photo every 6.0 m, and fly lines 8.1 m apart.
```

- The height is **above the tree tops**, not above the ground. If the trees are 12 m tall, set the drone to 12 + 28 = 40 m.
- `--pixels-across` sets how many pixels the target gets (default 10). Fewer pixels let you fly higher, but the detector finds fewer targets. The pine processionary study used about 7 pixels across a 5 cm nest (0.7 cm per pixel).
- For a camera that is not in the list, use `--focal-length` (35 mm equivalent) and `--image-size`.

## 3. Set the camera

- Point the camera **straight down** (gimbal pitch −90°). TickTerminator calculates map positions only for photos within 10° of straight down.
- Keep GPS on, and do not remove the photo metadata. TickTerminator reads the GPS position, the focal length and, for DJI drones, the height and the direction of the camera.
- Take photos (JPEG), not video. Video frames have no position data.

## 4. Fly a grid

Use a mapping app (for example DJI Pilot 2, Dronelink, Litchi or DroneDeploy) to fly parallel lines over the area. Use the photo spacing and line spacing from `tickterminator plan`. An overlap of 80% shows most targets in more than one photo, from different angles. This is important, because branches can hide a nest in one photo but not in the next.

Fly over edges first: forest edges, roadsides, fence rows and orchard borders. Tent caterpillars prefer trees at edges.

## 5. Scan the photos

Copy all photos into one folder, then:

```bash
tickterminator scan ./flight --pests tent_caterpillar
```

Open `report.html`. It shows each finding on a map, with its sector and a close-up. Go to the sectors and check the findings on the ground.

**Position accuracy.** DJI drones record the height above the take-off point. TickTerminator uses that height to calculate positions on flat ground. Tall trees and hills make the error larger. Expect positions to be a few meters wrong. Use the close-up and the sector to find the tree.

## 6. Improve the detector

The zero-shot detector makes errors. To make it better, correct its findings and train a model. See [Train a model](../README.md#train-a-model).

## Safety and the law

Know the drone rules in your country before you fly. In most countries, small drones must stay below 120 m (400 ft), within your line of sight, and away from people and airports. Some countries require a registration or a test, also for recreational flights. Get permission from the landowner.
