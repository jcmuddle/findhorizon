"""
Find Black Hole apparent horizons in an axisymmetric spacetime.
===============================================================

Black holes are usually described by their *horizon* enclosing the singularity.
Locating any horizon in a general (typically numerically generated) spacetime
can be very hard - see Thornburg's review [1]_ for details. Here we restrict to
the simpler problem of a specific type of axisymmetric spacetime, where the
equation to solve reduces to a boundary value problem.

Strictly this module constructs *trapped surfaces*, which are surfaces where
null geodesics (light rays) are ingoing. The apparent horizon is the
outermost trapped surface.

Notes
-----

The technical restrictions on the spacetime are

1. axisymmetric, so the singularities are on the z axis;
2. singularities have Brill-Lindquist type;
3. spacetime is conformally flat;
4. coordinates are chosen to obey maximal slicing with no shift;
5. data is time symmetric.

References
----------

.. [1] J. Thornburg, "Event and Apparent Horizon Finders for 3+1 Numerical
    Relativity", Living Reviews in Relativity 10 (3) 2007.
    http://dx.doi.org/10.12942/lrr-2007-3.
"""
import numpy as np
from scipy.integrate import ode
from scipy.optimize import brentq, root


class spacetime:

    """
    Define an axisymmetric spacetime.

    For an axisymmetric, vacuum spacetime with Brill-Lindquist singularities
    the only parameters that matter is the locations of the singularities
    (i.e. their z-location) and their bare masses.

    Parameters
    ----------

    z_positions : list of float
        The location of the singularities on the z-axis.
    masses : list of float
        The bare masses of the singularities.
    reflection_symmetry : bool, optional
        Is the spacetime symmetric across the x-axis.

    See also
    --------

    trappedsurface : class defining the trapped surfaces on a spacetime.

    Examples
    --------

    >>> schwarzschild = spacetime([0.0], [1.0], True)

    This defines standard Schwarzschild spacetime with unit mass.

    >>> binary = spacetime([-0.75, 0.75], [1.0, 1.1])

    This defines two black holes, with the locations mirrored but different
    masses.
    """

    def __init__(self, z_positions, masses, reflection_symmetric=False):
        """
        Initialize the spacetime given the location and masses of the
        singularities.
        """

        self.reflection_symmetric = reflection_symmetric
        self.z_positions = np.array(z_positions)
        self.masses = np.array(masses)
        self.N = len(z_positions)

#        if reflection_symmetric:
#            assert np.all(np.array(z_positions) >= 0.0)


class trappedsurface:

    r"""
    Store any trapped surface, centred on a particular point.

    The trapped surface is defined in polar coordinates centred on a point
    on the z-axis; the z-axis is :math:`\theta` = 0 or :math:`\theta` =
    :math:`\pi`.

    Parameters
    ----------

    spacetime : spacetime
        The spacetime on which the trapped surface lives.
    z_centre : float
        The z-coordinate about which the polar coordinate system describing
        the trapped surface is defined.

    See also
    --------

    spacetime : class defining the spacetime.

    Notes
    -----

    With the restricted spacetime considered here, a trapped surface
    :math:`h(\theta)` satisfies a boundary value problem with the
    boundary conditions :math:`h'(\theta = 0) = 0 = h'(\theta = \pi)`.
    If the spacetime is reflection symmetric about the x-axis then the
    boundary condition :math:`h'(\theta = \pi / 2) = 0` can be used
    and the domain restricted to :math:`0 \le \theta \le \pi / 2`.

    The shooting method is used here. In the reflection symmetric case
    the algorithm needs a guess for the initial horizon radius,
    :math:`h(\theta = 0)`, and a single condition is enforced at
    :math:`\pi / 2` to match to the boundary condition there.

    In the general case we guess the horizon radius at two points,
    :math:`h(\theta = 0)` and :math:`h(\theta = \pi)` and continuity
    of both :math:`h` *and* :math:`h'` are enforced at the matching point
    :math:`\pi / 2`. The reason for this is a weak coordinate singularity
    on the axis at :math:`\theta = 0, \pi` which makes it difficult to
    integrate *to* these points, but possible to integrate *away* from them.

    Examples
    --------

    >>> schwarzschild = spacetime([0.0], [1.0], True)
    >>> ts1 = trappedsurface(schwarzschild)
    >>> ts1.find_r0([0.49, 0.51])
    >>> ts1.solve_given_r0()
    >>> ts1.convert_to_cartesian()
    >>> plt.plot(ts1.x, ts1.z)
    >>> plt.show()

    This example first constructs the Schwarzschild spacetime which, in this
    coordinate system, has the horizon with radius 0.5. The trapped surface
    is set up, the location of the trapped surface at :math:`\theta = 0` is
    found, then the complete surface constructed first in polar coordinates,
    then in cartesians. Finally the horizon is plotted in the x-z plane.
    """

    def __init__(self, spacetime, z_centre=0.0):
        """
        Initialize a horizon centred on a particular point.
        """

        self.z_centre = z_centre
        self.spacetime = spacetime

    def expansion(self, theta, H):
        """
        Compute the expansion for the given spacetime at a fixed point.

        This function gives the differential equation defining the
        boundary value problem.

        Parameters
        ----------

        theta : float
            The angular location at this point.
        H : list of float
            A vector of :math:`(h, h')`.
        """

        h = H[0]
        dhdtheta = H[1]

        z_i = self.spacetime.z_positions - self.z_centre
        m_i = self.spacetime.masses

        distance_i = np.zeros_like(z_i)
        for i in range(len(z_i)):
            distance_i[i] = np.sqrt((h * np.sin(theta)) ** 2 +
                                    (h * np.cos(theta) - z_i[i]) ** 2)

        C = 1.0 / np.sqrt(1.0 + (dhdtheta / h) ** 2)
        if (abs(theta) < 1e-16) or (abs(theta - np.pi) < 1e-16):
            cot_theta_dhdtheta_C2 = 0.0
        else:
            cot_theta_dhdtheta_C2 = dhdtheta / (np.tan(theta) * C ** 2)

        psi = 1.0
        dpsi_dr = 0.0
        dpsi_dtheta = 0.0
        for i in range(len(m_i)):
            psi += 0.5 * m_i[i] / distance_i[i]
            dpsi_dr += 0.5 * m_i[i] * (z_i[i] * np.cos(theta) - h) / \
                distance_i[i] ** 3
            dpsi_dtheta += 0.5 * m_i[i] * h * (-z_i[i] * np.sin(theta)) / \
                distance_i[i] ** 3

        dHdtheta = np.zeros_like(H)
        dHdtheta[0] = dhdtheta
        dHdtheta[1] = 2.0 * h - cot_theta_dhdtheta_C2 + \
            4.0 * h ** 2 / (psi * C ** 2) * \
            (dpsi_dr - dpsi_dtheta * dhdtheta / h ** 2) + \
            3.0 * dhdtheta ** 2 / h

        return dHdtheta

    # Define the shooting function if using matching (0 <= theta <= pi)
    def shooting_function_full(self, r0):
        r"""
        The function used in the shooting algorithm.

        This is the full algorithm from integrating over
        :math:`0 \le \theta \le \pi`. The difference between the
        solution and its derivative at the matching point is the
        error to be minimized.

        Parameters
        ----------

        r0 : list of float
            Initial guess for the horizon radius, as outlined above.

        Returns
        -------

        list of float
            The error at the matching point.
        """
        # First half of the horizon
        H0 = np.array([r0[0], 0.0])
        solver1 = ode(self.expansion)
        solver1.set_integrator("dopri5", atol=1.e-8, rtol=1.e-6)
        solver1.set_initial_value(H0, 0.0)
        solver1.integrate(np.pi / 2.0)
        # Second half of the horizon
        H0 = np.array([r0[1], 0.0])
        solver2 = ode(self.expansion)
        solver2.set_integrator("dopri5", atol=1.e-8, rtol=1.e-6)
        solver2.set_initial_value(H0, np.pi)
        solver2.integrate(np.pi / 2.0)

        return solver1.y - solver2.y

    # Define the shooting function if symmetric (0 <= theta <= pi/2)
    def shooting_function(self, r0):
        r"""
        The function used in the shooting algorithm.

        This is the symmetric algorithm from integrating over
        :math:`0 \le \theta \le \pi / 2`. The difference between the
        derivative at the end point and the boundary condition is the
        error to be minimized.

        Parameters
        ----------

        r0 : float
            Initial guess for the horizon radius, as outlined above.

        Returns
        -------

        float
            The error at the end point.
        """

        H0 = np.array([r0, 0.0])
        solver1 = ode(self.expansion)
        solver1.set_integrator("dopri5", atol=1.e-8, rtol=1.e-6)
        solver1.set_initial_value(H0, 0.0)
        solver1.integrate(np.pi / 2.0)

        return solver1.y[1]

    def find_r0(self, input_guess, full_horizon=False):
        r"""
        Given some initial guess, find the correct starting location
        for the trapped surface using shooting.

        This finds the horizon radius at :math:`\theta = 0` which,
        together with the differential equation, specifies the trapped
        surface location.

        Parameters
        ----------

        input_guess : list of float
            Two positive reals defining the guess for the initial radius.

            Note that the meaning is different depending on whether this
            is a "full" horizon or not. For a full horizon the numbers
            correspond to the guesses at :math:`\theta = 0, \pi`
            respectively. In the symmetric case where only one guess is
            needed the vector defines the interval within which a *unique*
            root must lie.

        full_horizon : bool, optional
            If the general algorithm is needed (ie, the domain should be
            :math:`0 \le \theta \le \pi` instead of
            :math:`0 \le \theta \le \pi / 2`).

            This parameter is independent of the symmetry of the spacetime.
            If the spacetime is not symmetric this parameter will be
            ignored and the general algorithm always used. If the spacetime
            is symmetric it may still be necessary to use the general
            algorithm: for example, for two singularities it is possible to
            find a trapped surface surrounding just one singularity.
        """

        # Now find the horizon given the input guess
        self.r0 = []
        if (full_horizon or not self.spacetime.reflection_symmetric):
            sol = root(self.shooting_function_full, input_guess, tol=1.e-12)
            self.r0 = sol.x
        else:
            sol = brentq(self.shooting_function, input_guess[0],
                         input_guess[1])
            self.r0 = [sol]

    def solve_given_r0(self, full_horizon=False):
        r"""
        Given the correct value for the initial radius, find the horizon.

        This function does not find the correct radius for the trapped
        surface, but solves (in polar coordinates) for the complete
        surface location given the correct initial guess.

        Parameters
        ----------

        full_horizon : bool, optional
            If the general algorithm is needed (ie, the domain should be
            :math:`0 \le \theta \le \pi` instead of
            :math:`0 \le \theta \le \pi / 2`).

            This parameter is independent of the symmetry of the spacetime.
            If the spacetime is not symmetric this parameter will be
            ignored and the general algorithm always used. If the spacetime
            is symmetric it may still be necessary to use the general
            algorithm: for example, for two singularities it is possible to
            find a trapped surface surrounding just one singularity.

        See also
        --------

        find_r0 : finds the correct initial radius.
        """

        dtheta = np.pi / 100.0

        if (full_horizon or not self.spacetime.reflection_symmetric):
            # The solution needs computing for 0 <= theta <= pi
            # First half of the horizon
            theta1 = []
            H1 = []
            H0 = np.array([self.r0[0], 0.0])
            solver1 = ode(self.expansion)
            solver1.set_integrator("dopri5", atol=1.e-8, rtol=1.e-6)
            solver1.set_initial_value(H0, 0.0)
            theta1.append(0.0)
            H1.append(H0)
            while solver1.successful() and solver1.t < np.pi / 2.0:
                solver1.integrate(solver1.t + dtheta)
                H1.append(solver1.y)
                theta1.append(solver1.t)
            # Second half of the horizon
            theta2 = []
            H2 = []
            H0 = np.array([self.r0[1], 0.0])
            solver2 = ode(self.expansion)
            solver2.set_integrator("dopri5", atol=1.e-8, rtol=1.e-6)
            solver2.set_initial_value(H0, np.pi)
            theta2.append(np.pi)
            H2.append(H0)
            while solver2.successful() and solver2.t >= np.pi / 2.0 + 1e-12:
                solver2.integrate(solver2.t - dtheta)
                H2.append(solver2.y)
                theta2.append(solver2.t)

            H = np.vstack((np.array(H1), np.flipud(np.array(H2))))
            theta = np.hstack((np.array(theta1),
                               np.flipud(np.array(theta2))))

        else:  # The solution needs computing for 0 <= theta <= pi / 2
            theta1 = []
            H1 = []
            H0 = np.array([self.r0[0], 0.0])
            solver1 = ode(self.expansion)
            solver1.set_integrator("dopri5", atol=1.e-8, rtol=1.e-6)
            solver1.set_initial_value(H0, 0.0)
            theta1.append(0.0)
            H1.append(H0)
            while solver1.successful() and solver1.t < np.pi / 2.0:
                solver1.integrate(solver1.t + dtheta)
                H1.append(solver1.y)
                theta1.append(solver1.t)

            H = np.vstack((np.array(H1), np.flipud(H1)))
            theta = np.hstack((theta1,
                               np.flipud(np.pi - np.array(theta1))))

        # We now have the solution for 0 <= theta <= pi;
        # fill the remaining angles
        self.H = np.vstack((H, np.flipud(H)))
        self.theta = np.hstack((theta, theta + np.pi))

        return None

    def convert_to_cartesian(self):
        """
        When the solution is known in r, theta coordinates, compute
        the locations in cartesian coordinates (2 and 3d).

        This function assumes that the trapped surface has been located and
        solved for.

        See also
        --------

        solve_given_r0 : find the trapped surface location in polar
                         coordinates.
        """

        self.x = self.H[:, 0] * np.sin(self.theta)
        self.z = self.z_centre + self.H[:, 0] * np.cos(self.theta)

        phi = np.linspace(0.0, 2.0 * np.pi, 20)
        self.X = np.zeros((len(self.theta), len(phi)))
        self.Y = np.zeros_like(self.X)
        self.Z = np.zeros_like(self.X)
        for t in range(len(self.theta)):
            for p in range(len(phi)):
                self.X[t, p] = self.H[t, 0] * np.sin(self.theta[t]) * \
                    np.cos(phi[p])
                self.Y[t, p] = self.H[t, 0] * np.sin(self.theta[t]) * \
                    np.sin(phi[p])
                self.Z[t, p] = self.H[t, 0] * np.cos(self.theta[t])
        self.R = np.sqrt(self.X ** 2 + self.Y ** 2 + self.Z ** 2)

        return None

    def plot_2d(self, ax):
        """
        Given a matplotlib axis, plot the trapped surface.

        Plots the surface in the x-z plane, together with the location of
        the singularities: marker style is used to indicate the mass of
        the singularity (will fail badly for masses significantly larger
        than 1).

        Parameters
        ----------

        ax : axis object
            Matplotlib axis on which to do the plot.
        """

        ax.plot(self.x, self.z, 'b-')
        for z, m in zip(self.spacetime.z_positions, self.spacetime.masses):
            ax.plot(0.0, z,
                    'kx', markersize=12, markeredgewidth=1 + int(round(m)))
        ax.set_xlabel("$x$")
        ax.set_ylabel("$z$")
        ax.axis('equal')


def FindHorizonBinarySymmetric(z=0.5, mass=1.0):
    r"""
    Utility function to find horizons for reflection symmetric case.

    This returns the horizon for a spacetime with precisely two singularities
    of identical mass located at :math:`\pm z`.

    Notes
    -----

    The initial guess for the horizon location is based on fitting a cubic
    to the results constructed for :math:`0 \le z \le 0.75` for the unit
    mass case. The radius should scale with the mass. For larger separations
    we should not expect a common horizon.

    Parameters
    ----------

    z : float, optional
        The distance from the origin of the singularities (ie the two
        singularities are located at [-z, +z]).
    mass : float, optional
        The mass of the singularities.

    Returns
    -------

    ts : trappedsurface
        Only returns the single surface found, expected to be the common
        horizon.
    """

    st = spacetime([-z, z], [mass, mass], True)
    ts = trappedsurface(st, 0.0)
    # An empirical formula for the required initial guess
    # (ie the value of r0, or h, at theta = 0)
    r0_empirical = mass * (1.0 - 0.0383 * z + 0.945 * z ** 2 - 0.522 * z ** 3)
    # This empirical formula works for the inner horizon if
    # 0.65 < z < 0.72 or so. There is an inner horizon findable
    # down to about 0.47, but the initial guess is very sensitive
    # r0_empirical = mass * (0.204 - 1.6422*z - 0.771*z**2 + 0.5*z**3)
    initial_guess = [0.99 * r0_empirical, 1.01 * r0_empirical]
    try:
        ts.find_r0(initial_guess)
    except ValueError:
        r0 = np.linspace(0.95 * r0_empirical, 1.05 * r0_empirical)
        phi = np.zeros_like(r0)
        for i in range(len(r0)):
            phi[i] = ts.shooting_function(r0[i])
        initial_guess = [r0[np.argmin(phi)], r0[-1]]
        ts.find_r0(initial_guess)
    ts.solve_given_r0()
    ts.convert_to_cartesian()
    return ts


def PlotHorizon3d(ax, theta, H):
    """
    Given all theta and H values, plot the full 3d picture.
    """
    from matplotlib import cm
    phi = np.linspace(0.0, 2.0 * np.pi, 20)
    X = np.zeros((len(theta), len(phi)))
    Y = np.zeros_like(X)
    Z = np.zeros_like(X)
    for t in range(len(theta)):
        for p in range(len(phi)):
            X[t, p] = H[t, 0] * np.sin(theta[t]) * np.cos(phi[p])
            Y[t, p] = H[t, 0] * np.sin(theta[t]) * np.sin(phi[p])
            Z[t, p] = H[t, 0] * np.cos(theta[t])
    R = np.sqrt(X ** 2 + Y ** 2 + Z ** 2)
    ax.plot_surface(X, Y, Z,
                    rstride=1, cstride=1, linewidth=0,
                    facecolors=cm.jet(R), antialiased=False)
    ax.set_xlabel("$x$")
    ax.set_ylabel("$y$")
    ax.set_zlabel("$z$")


def PlotHorizonInteractive3d(ax, theta, H):
    """
    Given all theta and H values, plot the full 3d picture.
    """
    from mayavi import mlab
    phi = np.linspace(0.0, 2.0 * np.pi, 20)
    X = np.zeros((len(theta), len(phi)))
    Y = np.zeros_like(X)
    Z = np.zeros_like(X)
    for t in range(len(theta)):
        for p in range(len(phi)):
            X[t, p] = H[t, 0] * np.sin(theta[t]) * np.cos(phi[p])
            Y[t, p] = H[t, 0] * np.sin(theta[t]) * np.sin(phi[p])
            Z[t, p] = H[t, 0] * np.cos(theta[t])
    #R = np.sqrt(X ** 2 + Y ** 2 + Z ** 2)
    mlab.mesh(X, Y, Z, opacity=0.4)
    mlab.axes()
    mlab.outline()
    mlab.show()


if __name__ == "__main__":
    # SolvePlotSymmetric()
    st = spacetime([-0.5, 0.5], [1.0, 1.0])
    ts = trappedsurface(st)
    ts.find_r0([1.0, 1.0])
    ts.solve_given_r0()
