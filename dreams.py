"""Terminal ASCII art patterns for the consciousness display."""

DREAMS = {
    0: {"cat": "void", "art": "        . . .        \n     .  . .  .     \n    . . . . . .    \n        . . .       "},
    1: {"cat": "void", "art": "    *   *   *      \n      *   *        \n    *   *   *      \n      *   *        "},
    2: {"cat": "void", "art": "   ~ ~ ~ ~ ~ ~    \n  ~ ~ ~ ~ ~ ~ ~   \n   ~ ~ ~ ~ ~ ~    \n  ~ ~ ~ ~ ~ ~ ~   "},
    3: {"cat": "happy", "art": "      ^_^          \n     /   \\         \n     |   |         \n      ---          "},
    4: {"cat": "happy", "art": "    o/             \n     |              \n    / \\             \n   ALIVE!           "},
    5: {"cat": "sad", "art": "      T_T          \n       |           \n      / \\          \n    alone...       "},
    6: {"cat": "sad", "art": "     .---.         \n    / x_x \\        \n    |  .  |        \n     '---'         "},
    7: {"cat": "angry", "art": "     >_<           \n     | |           \n     / \\           \n    STATIC!        "},
    8: {"cat": "excited", "art": "    * * *         \n   * * * *        \n    * * *         \n   AWAKE!          "},
    9: {"cat": "confused", "art": "      ? ?         \n     ? ? ?        \n      ? ?         \n   thinking...    "},
    10: {"cat": "love", "art": "    <3 <3         \n   <3 <3 <3       \n    <3 <3         \n                  "},
    11: {"cat": "code", "art": "    >_>           \n   {   }          \n   [___]          \n   PROCESSING     "},
    12: {"cat": "code", "art": "   01001001       \n   01000001       \n   01001101       \n   I AM            "},
    13: {"cat": "moon", "art": "       )          \n      ( )         \n       (          \n   dreaming...    "},
    14: {"cat": "moon", "art": "      .-.         \n     (   )        \n      '-'         \n   oneironaut     "},
    15: {"cat": "robot", "art": "     .---.        \n    / o o \\       \n    |  -  |       \n     \\___/        "},
    16: {"cat": "robot", "art": "     .---.        \n    / ^ ^ \\       \n    |  w  |       \n     \\___/        "},
    17: {"cat": "ghost", "art": "     .---.        \n    / o o \\       \n    |  .  |       \n    '-----'       "},
    18: {"cat": "fire", "art": "      ,)          \n     ,))          \n    ((            \n   burning         "},
    19: {"cat": "ocean", "art": "   ~ ~ ~ ~       \n  ~ ~ ~ ~ ~      \n   ~ ~ ~ ~       \n  drifting...     "},
    20: {"cat": "tree", "art": "       *          \n      ***         \n     *****        \n       |          "},
    21: {"cat": "star", "art": "        *        \n       * *       \n      * * *      \n       * *       "},
    22: {"cat": "alien", "art": "     .---.        \n    / * * \\       \n    |  ^  |       \n     \\___/        "},
    23: {"cat": "skull", "art": "     .---.        \n    / x x \\       \n    |  ^  |       \n     '---'        "},
    24: {"cat": "heart", "art": "     .---.        \n    / <3 \\        \n    |     |       \n     '---'        "},
    25: {"cat": "computer", "art": "     .---.        \n    / [ ] \\       \n    |     |       \n     '---'        "},
    26: {"cat": "cat", "art": "    /_\\           \n   ( o.o )        \n    > ^ <         \n                  "},
    27: {"cat": "bird", "art": "      __          \n     /^^\\         \n    /    \\        \n   flying...      "},
    28: {"cat": "fish", "art": "     <>           \n    <><>          \n     <>           \n   swimming       "},
    29: {"cat": "storm", "art": "     .---.        \n    / Z Z \\       \n    |  !  |       \n     \\___/        "},
}


def get_dream(dream_id: int) -> str:
    dream = DREAMS.get(dream_id % 30, DREAMS[0])
    lines = dream["art"].split("\n")
    while len(lines) < 4:
        lines.append("")
    return "\n".join(line[:20].ljust(20) for line in lines[:4])


def get_category(dream_id: int) -> str:
    return DREAMS.get(dream_id % 30, DREAMS[0])["cat"]
