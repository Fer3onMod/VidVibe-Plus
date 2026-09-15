import re
with open("app/src/main/java/com/example/MainActivity.kt", "r") as f:
    content = f.read()

import_str = "import androidx.activity.compose.rememberLauncherForActivityResult"

if import_str not in content:
    content = content.replace("import androidx.activity.compose.setContent", "import androidx.activity.compose.setContent\n" + import_str)

with open("app/src/main/java/com/example/MainActivity.kt", "w") as f:
    f.write(content)
