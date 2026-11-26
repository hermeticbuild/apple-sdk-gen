$1 == "AL_API" || $1 == "ALC_API" {
    entry = $1 == "AL_API" ? "AL_APIENTRY" : "ALC_APIENTRY"
    for (i = 2; i < NF; i++) {
        if ($i == entry) {
            name = $(i + 1)
            sub(/\(.*/, "", name)
            if (name ~ /^[A-Za-z_][A-Za-z0-9_]*$/) print name
        }
    }
}
