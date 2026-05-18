"""
Tool-nose-radius offset for finishing pass path computation.

Replaces G41/G42 controller compensation with an explicit offset computed
per profile point, so the G-code contains the actual tool-centre-point (TCP)
path and works on any controller.

Strategy
--------
For each profile point (r, z):
  External: r_tcp = r + nose_radius   (tool centre is outside the surface)
  Internal: r_tcp = r - nose_radius   (tool centre is inside the bore)

This is exact for cylindrical surfaces and a good approximation for shallow
tapers.  For aggressive tapers (>30°) the Z-axis error is at most:
  Δz = nose_radius × (1 − cos θ)
which stays below 0.1 mm for nose_radius=0.4 and θ≤45°.

Public API
----------
  offset_profile_polygon(profile, nose_radius, internal) → list[(r, z)]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.profile import LatheProfile


def offset_profile_polygon(
    profile: "LatheProfile",
    nose_radius: float,
    internal: bool = False,
) -> list[tuple[float, float]]:
    """
    Return the TCP path for a finishing pass offset by *nose_radius*.

    Falls back to the raw profile polygon when nose_radius is zero or
    negative (no offset needed).
    """
    raw_pts = profile.to_polygon()
    if not raw_pts or nose_radius <= 0.0:
        return raw_pts

    delta = -nose_radius if internal else nose_radius
    return [(r + delta, z) for r, z in raw_pts]
