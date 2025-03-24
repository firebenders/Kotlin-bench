MAP_REPO_VERSION_TO_SPECS_KT = {
    "wordpress-mobile/WordPress-Android": {
        k: {
            "kotlin": "1.9.21",
            "packages": "gradle",
            "install": "./gradlew assembleDebug",
            "test_cmd": "./gradlew test",
        }
        for k in ["0.7", "0.8", "0.9", "0.11", "0.13", "0.14", "1.1", "1.2", "2.0", "2.2"]
        + ["2.3", "2.4", "2.5", "2.7", "2.8", "2.9", "2.10", "2.11", "2.12", "2.17"]
        + ["2.18", "2.19", "2.22", "2.26", "2.25", "2.27", "2.31", "3.0"]
    }
}

MAP_REPO_TO_INSTALL_KT = {}