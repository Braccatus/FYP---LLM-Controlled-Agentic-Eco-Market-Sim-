import pynetlogo

nl = pynetlogo.NetLogoLink(gui=False, netlogo_home='C:/Program Files/NetLogo 7.0.2')
nl.load_model('C:/Program Files/NetLogo 7.0.2/models/Sample Models/Social Science/Economics/Wealth Distribution.nlogox')
nl.command('setup')
nl.command('go')

print("gini:", nl.report('gini-index-reserve'))
print("wealth turtle 0:", nl.report('[wealth] of turtle 0'))
print("low class:", nl.report('count turtles with [color = red]'))
print("mid class:", nl.report('count turtles with [color = green]'))
print("up class:", nl.report('count turtles with [color = blue]'))

nl.kill_workspace()