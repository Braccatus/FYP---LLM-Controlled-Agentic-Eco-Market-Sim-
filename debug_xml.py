xml = """<experiments>
  <experiment name="wealth_sim" repetitions="1" sequentialRunOrder="true" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <timeLimit steps="100"></timeLimit>
    <metrics>
      <metric>gini-index-reserve</metric>
    </metrics>
    <constants>
      <enumeratedValueSet variable="num-people">
        <value value="250"></value>
      </enumeratedValueSet>
    </constants>
  </experiment>
</experiments>"""

with open("debug_experiment.xml", "w") as f:
    f.write(xml)
print("Written to debug_experiment.xml")