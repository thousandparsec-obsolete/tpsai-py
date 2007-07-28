
import hotshot, hotshot.stats
stats = hotshot.stats.load("hotshot_stats")
#stats.strip_dirs()
stats.sort_stats('time', 'calls')
stats.print_stats(500)
