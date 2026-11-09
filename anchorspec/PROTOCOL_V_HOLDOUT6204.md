# Additional geometry check frozen after HUST6205..6208 scores

Transport (without healthy mixing) improved mean recall for all six combinations
of three fixed classifiers and two unit assumptions in HUST6205..6208. Select this
method for an explicit further check. This selection is post-development; preserve
all earlier negative results. No method or parameters will be changed on6204.

Acquire N400,N402,N404,I400,I402,I404,O400,O402,O404 from publisher V3, SHA256
verify all9. These files were not in the V development subset. 6204 has no B file,
so report inner/outer only, never compare its two-class accuracy directly with
the three-class development average. Six ordered load transfers, three seeds,
two unit assumptions;36 tasks. Same generator, 64 samples/class, mass0.5,
same six methods and three classifiers from v_external. Primary SVM C1,
primary augmentation transport. No validation or test-based model selection.

Sample rate51200, first1s discarded, up to6s healthy and10s fault, complete1s
windows. Geometry8balls,7.6mm diameter, pitch33.5mm approximation. Source fault
speed metadata for donor, target healthy speed only for target. Apply same sensor.

Success for this additional check: transport beats real, duplicate and legacy
surrogate in macro recall for BOTH unit assumptions with SVM C1; neither class
loses more than5points versus real. Report all other models as sensitivity.
This tests an additional bearing geometry within the same acquisition study.
Repeated loads may share a fault specimen. It does not resolve unknown units,
independent-machine performance, lubrication, contamination, RUL or factory scope.
