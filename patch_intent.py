import re
with open("app/src/main/java/com/example/MainActivity.kt", "r") as f:
    content = f.read()

# Fix the type inference on ActivityResultContracts.RequestMultiplePermissions()
content = content.replace("val permissionLauncher = rememberLauncherForActivityResult(", "val permissionLauncher = rememberLauncherForActivityResult<Array<String>, Map<String, @JvmSuppressWildcards Boolean>>(")

with open("app/src/main/java/com/example/MainActivity.kt", "w") as f:
    f.write(content)
