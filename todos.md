***ToDo's***

**low**
- implement Python code conventions. Like underscore thing for variables and functions
see https://google.github.io/styleguide/pyguide.html


DLP: Depreciation of attribute "totalHeightWithExtrusion"
I will drop the attribute "totalHeightWithExtrusion" and "totalWithExtrusion" from event- and api-payload in my next release (1.18.x. or 1.19.x)

Reason:
I fixed the behaviour of the "total-height-mode". Depending on the mode-setting the corresponding height value will be used as "totalHeight"
So, please change your implementation from:
