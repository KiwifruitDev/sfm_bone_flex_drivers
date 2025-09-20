# SFM Bone Flex Drivers Script
Map bones to flexes, just like shape key drivers!

This script replicates the [$boneflexdriver](https://developer.valvesoftware.com/wiki/$boneflexdriver) QC command for use in Source Filmmaker.

This allows you to control flexes automatically using a bone's position or rotation, replicating the shape key driver/control bone feature found in Blender.

Video above provided by [Smug Bastard](https://steamcommunity.com/profiles/76561198027986401).

## Setup
*(Optional) Install [Autoinit Manager](https://steamcommunity.com/sharedfiles/filedetails/?id=3400621327) and activate this script within it.*

Otherwise, open the Bone Flex Drivers Window by clicking "Scripts" at the top menu bar -> "kiwifruitdev" -> "bone_flex_drivers"

Inside of the Bone Flex Drivers Window, select a shot and an animation set.

Each bone flex driver will be listed in the window, where you can select and edit their properties.

## Usage

Click "Add" to add a new bone flex driver using a bone and flex, though flexes cannot be shared between multiple drivers.

After setting up a bone flex driver, you may choose an axis (X, Y, or Z), set which movement type to use, and set the minimum and maximum values for the bone.

The "clamp" option is available to restrict the flex value between 0 and 1, and you may also set minimum and maximum flex values.

The flex value will be calculated based on the bone's position or rotation within the specified range, even without the script running.

## Known Issues
When using an animation set affected by a rig script with bone flex drivers, you may face crashes in SFM.

Also, the bone axises Y and Z have not been fully tested. Please report any issues you find.

## Development
This script is also available on [GitHub](https://github.com/KiwifruitDev/sfm_bone_flex_drivers).

## License
This script is licensed under the [MIT License](https://github.com/KiwifruitDev/sfm_bone_flex_drivers/blob/main/LICENSE).
