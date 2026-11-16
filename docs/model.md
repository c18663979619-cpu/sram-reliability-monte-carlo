# Model, units, and numerical method

## Behavioral definition

For each inverter:

$$V_M=(V_{DD}-V_{th,p}+V_{th,n})/2,$$

$$f(V_{in})=\frac{V_{DD}}{1+\exp[g(V_{in}-V_M)]},\qquad g=14\;\mathrm{V}^{-1}.$$

`Vth,p` is a positive threshold magnitude in this switching-point rule. All model inputs are in volts. This empirical rule has no device currents, transistor sizing, access transistors, or calibrated technology parameters. Equal n/p threshold shifts cancel in this rule, illustrating a limitation of this simplified model.

The main sampling distribution is

$$V_{th}\sim\mathcal{N}(0.40\;\mathrm{V},(0.04\;\mathrm{V})^2).$$

The second argument above is the variance. `sigma_v` in Python is the standard deviation. Four independent draws define n1, p1, n2, p2. A local MT19937 generator with seed 42 preserves the original notebook's column-by-column sample order without changing global random state. The 30 mV histogram is a separate illustration.

## Diagonal SNM construction

The butterfly boundaries are `(x, f1(x))` and `(f2(y), y)`. On a diagonal `c = y-x`, invert:

- `f1(x1)-x1 = c`;
- `y2-f2(y2) = c`, with `x2 = f2(y2)`.

The two points share this diagonal, so their horizontal and vertical separations are equal: the candidate square side is `abs(x1-x2)`. Work only on the overlap of the two VTCs' diagonal domains. Locate the three intersections; measure the maximum separation within each of the two intervening closed lobes, and take the smaller maximum. If a sampled curve pair does not resolve three intersections, return zero margin. Near a vanishing lobe, refine the grid before interpreting this zero physically.

The production routine shares an interpolated base curve across a batch of samples. The default uses 4,097 base-curve points, 1,001 diagonal points, and batches of 256. This keeps memory proportional to one batch rather than all supply/sample/grid combinations at once. Loops over batches and supply voltages are intentional.

The reference solves each physical VTC by 48 bisection iterations and scans 20,001 diagonals. It uses separate intersection/lobe code. The reference is still a numerical approximation to the same behavioral model.

## Supply scaling

The default keeps `g = 14 V^-1` fixed in physical voltage units for every supply. The earlier supply-sweep cell held the normalized VTC shape fixed, equivalent to `g = 14 / VDD` in physical units. These assumptions coincide at 1.0 V and give different trends elsewhere. Neither has been calibrated against transistor simulation; the default makes the first butterfly calculation and the sweep internally consistent.

Threshold samples are reused across supplies to make a paired comparison. Pointwise Wilson intervals do not imply independence between voltages or simultaneous coverage of the whole curve.

## Statistics

SNM standard deviation uses `ddof=0` to summarize the generated population; the empirical 1st percentile uses NumPy's default linear quantile interpolation. “Below criterion” means strictly `< 0.180 V`. This is a chosen parametric criterion, not a demonstrated read, write, or retention failure.

For `k` events in `n` samples, the Wilson interval uses `z = Phi^-1(0.975)`:

$$\frac{\hat p+z^2/(2n)\;\pm\;z\sqrt{\hat p(1-\hat p)/n+z^2/(4n^2)}}{1+z^2/n}.$$

See [NIST](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm). It represents sampling uncertainty conditional on the model. Physical modeling error, parameter uncertainty, and numerical error are separate.
