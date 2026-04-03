def lerp(a, b, t) -> float:
    return a + (b - a) * t

def lerp_color(c1, c2, t) -> tuple[float, float, float]:
    return (
        lerp(c1[0], c2[0], t),
        lerp(c1[1], c2[1], t),
        lerp(c1[2], c2[2], t),
    )

def sample_gradient(colors, t: float) -> tuple[float, float, float]:
    n = len(colors)
    if n == 0:
        raise ValueError("No colors provided")
    if n == 1:
        return colors[0]

    # Clamp t
    t = max(0.0, min(1.0, t))

    scaled = t * (n - 1)
    i = int(scaled)

    # Handle edge case at t = 1
    if i >= n - 1:
        return colors[-1]

    local_t = scaled - i
    return lerp_color(colors[i], colors[i + 1], local_t)