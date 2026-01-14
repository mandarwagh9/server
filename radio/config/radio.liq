#!/usr/bin/liquidsoap

settings.log.level.set(4)

host = "icecast"
port = 8000
password = "hackme"

daftpunk = playlist(mode="randomize", reload=3600, "/music/daftpunk")
lifafa = playlist(mode="randomize", reload=3600, "/music/lifafa")
marathi = playlist(mode="randomize", reload=3600, "/music/marathi")
hindiold = playlist(mode="randomize", reload=3600, "/music/hindiold")
gazals = playlist(mode="randomize", reload=3600, "/music/gazals")
roadtrip = playlist(mode="randomize", reload=3600, "/music/roadtrip")
rap = playlist(mode="randomize", reload=3600, "/music/rap")

daftpunk = fallback(track_sensitive=false, [daftpunk, sine(440.)])
lifafa = fallback(track_sensitive=false, [lifafa, sine(523.)])
marathi = fallback(track_sensitive=false, [marathi, sine(659.)])
hindiold = fallback(track_sensitive=false, [hindiold, sine(784.)])
gazals = fallback(track_sensitive=false, [gazals, sine(880.)])
roadtrip = fallback(track_sensitive=false, [roadtrip, sine(987.)])
rap = fallback(track_sensitive=false, [rap, sine(1046.)])

output.icecast(%mp3, host=host, port=port, password=password, mount="daftpunk", name="Daft Punk Radio", description="24/7 Daft Punk", daftpunk)
output.icecast(%mp3, host=host, port=port, password=password, mount="lifafa", name="Lifafa Radio", description="24/7 Lifafa", lifafa)
output.icecast(%mp3, host=host, port=port, password=password, mount="marathi", name="Marathi Radio", description="24/7 Marathi Songs", marathi)
output.icecast(%mp3, host=host, port=port, password=password, mount="hindiold", name="Hindi Old Radio", description="24/7 Classic Hindi", hindiold)
output.icecast(%mp3, host=host, port=port, password=password, mount="gazals", name="Gazals Radio", description="24/7 Gazals", gazals)
output.icecast(%mp3, host=host, port=port, password=password, mount="roadtrip", name="Road Trip Radio", description="24/7 Road Trip Music", roadtrip)
output.icecast(%mp3, host=host, port=port, password=password, mount="rap", name="Rap Radio", description="24/7 Rap & Hip-Hop", rap)
