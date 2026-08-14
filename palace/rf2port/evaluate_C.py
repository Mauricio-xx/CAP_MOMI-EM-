import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import skrf as rf


def differential_capacitance_from_admittance(frequency, differential_admittance):
    capacitance = np.full(frequency.shape, np.nan, dtype=float)
    valid = (frequency > 0) & (np.abs(np.imag(differential_admittance)) > 0)
    capacitance[valid] = np.imag(differential_admittance[valid]) / (2.0 * np.pi * frequency[valid])
    return capacitance


def get_reference_impedance(network):
    z0 = np.asarray(network.z0)
    if z0.ndim == 0:
        return np.full(network.f.shape, z0, dtype=complex)

    if z0.ndim == 1:
        return np.asarray(z0, dtype=complex)

    if z0.shape[1] != 2:
        raise ValueError("Expected a 2-port Touchstone file")

    if not np.allclose(z0[:, 0], z0[:, 1]):
        raise ValueError("Differential processing requires equal reference impedance on both ports")

    return np.asarray(z0[:, 0], dtype=complex)


def process_s2p(s2p_filename, gds_name=None, results_dir=None):
    network = rf.Network(s2p_filename)
    if network.number_of_ports != 2:
        raise ValueError(f"Expected a 2-port Touchstone file, got {network.number_of_ports} ports")

    label = gds_name or Path(s2p_filename).stem
    if results_dir is None:
        results_dir = Path(__file__).resolve().parent / "results"
    else:
        results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    results_txt_path = results_dir / "results.txt"

    f = network.f
    s11 = network.s[:, 0, 0]
    s21 = network.s[:, 1, 0]
    s12 = network.s[:, 0, 1]
    s22 = network.s[:, 1, 1]

    z0 = get_reference_impedance(network)
    y0 = 1.0 / z0
    denominator = (1 + s11) * (1 + s22) - s12 * s21
    y11 = y0 * ((1 - s11) * (1 + s22) + s12 * s21) / denominator
    y12 = y0 * (-2 * s12) / denominator
    y21 = y0 * (-2 * s21) / denominator
    y22 = y0 * ((1 + s11) * (1 - s22) + s12 * s21) / denominator

    ydd = -0.5 * (y12 + y21)
    zdd = 1.0 / ydd
    cdd = differential_capacitance_from_admittance(f, ydd)

    target_frequency = 0.06e9
    target_index = np.argmin(np.abs(f - target_frequency))
    target_capacitance_ff = None

    print("\nStarting plots")
    if np.isfinite(cdd[target_index]):
        target_capacitance_ff = cdd[target_index] * 1e15
        print(
            f"Extracted differential capacitance at {f[target_index] / 1e9:.3f} GHz: "
            f"{target_capacitance_ff:.2f} fF"
        )

 #   plt.figure()
 #   plt.plot(f / 1e9, np.real(zdd), "k-", linewidth=2, label="Re(Zdd) [Ohm]")
 #   plt.plot(f / 1e9, np.imag(zdd), "r-", linewidth=2, label="Im(Zdd) [Ohm]")
 #   plt.xscale("log")
 #   plt.grid(True, which="both")
 #   plt.legend()
 #   plt.xlabel("Frequency (GHz)")
 #   plt.ylabel("Impedance (Ohm)")

    valid_capacitance = np.isfinite(cdd)

    plt.figure()
    plt.plot(
        f[valid_capacitance] / 1e9,
        cdd[valid_capacitance] * 1e15,
        "k-",
        linewidth=2,
        label="Differential capacitance from Ydd [fF]",
    )
    if np.isfinite(cdd[target_index]):
        target_frequency_ghz = f[target_index] / 1e9
        plt.plot(target_frequency_ghz, target_capacitance_ff, "ro")
        plt.annotate(
            f"{label} - {target_capacitance_ff:.2f} fF",
            xy=(target_frequency_ghz, target_capacitance_ff),
            xytext=(10, 10),
            textcoords="offset points",
            arrowprops=dict(arrowstyle="->"),
        )
    plt.xscale("log")
    plt.grid(True, which="both")
    plt.legend()
    plt.xlabel("Frequency (GHz)")
    plt.ylabel("Capacitance (fF)")
    plt.title(f"Capacitance from {label}")

    output_path = results_dir / f"{label}.png"
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()

    value = "nan" if target_capacitance_ff is None else f"{target_capacitance_ff:.6f}"
    existing_lines = []
    if results_txt_path.exists():
        existing_lines = results_txt_path.read_text(encoding="ascii").splitlines()

    updated_lines = []
    replaced = False
    for line in existing_lines:
        parts = line.split()
        if parts and parts[0] == label:
            updated_lines.append(f"{label}\t{value}")
            replaced = True
        else:
            updated_lines.append(line)

    if not replaced:
        updated_lines.append(f"{label}\t{value}")

    results_txt_path.write_text("\n".join(updated_lines) + "\n", encoding="ascii")
    print(f"Wrote plot to {output_path}")
    print(f"Updated result in {results_txt_path}")
    return output_path, target_capacitance_ff


def main():
    parser = argparse.ArgumentParser(description="Process a 2-port Touchstone .s2p file.")
    parser.add_argument("s2p_file", help="Path to the .s2p file to process")
    parser.add_argument("--gds-name", help="Name used for plot labeling and output file naming")
    parser.add_argument("--results-dir", help="Directory where plots should be written")
    args = parser.parse_args()

    process_s2p(args.s2p_file, gds_name=args.gds_name, results_dir=args.results_dir)


if __name__ == "__main__":
    main()
