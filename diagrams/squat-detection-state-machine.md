
```mermaid
stateDiagram-v2
    [*] --> Unknown
    Unknown --> Standing: angle > 160°
    Standing --> Descending: angle decreasing
    Descending --> Bottom: angle < 100°
    Bottom --> Ascending: angle increasing
    Ascending --> Standing: angle > 160°
    Standing --> [*]: session_end
```
