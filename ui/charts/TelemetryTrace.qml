import QtQuick
import CarDiagnostic
Canvas {
    id: trace
    property var samples: []
    onSamplesChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        const c = getContext("2d")
        c.clearRect(0,0,width,height)
        const points = samples.filter(function(sample) { return typeof sample.value === "number" && isFinite(sample.value) })
        if(points.length < 2) return
        const values = points.map(function(point) { return point.value })
        const low = Math.min.apply(null,values), high = Math.max.apply(null,values)
        const range = high - low || 1
        const first = points[0].at, last = points[points.length-1].at
        c.strokeStyle = Neo.blue; c.lineWidth = 2; c.beginPath()
        for(let i=0;i<points.length;i++) {
            const x = 2 + (points[i].at - first) / Math.max(1,last-first) * (width-4)
            const y = height - 3 - (points[i].value-low) / range * (height-6)
            if(i===0) c.moveTo(x,y); else c.lineTo(x,y)
        }
        c.stroke()
    }
    Accessible.role: Accessible.Chart
    Accessible.name: qsTr("Recent measured samples; no simulated values")
}
