# main.py
import sys, platform, math
import torch, pyro
import pyro.distributions as dist
from pyro.infer import SVI, Trace_ELBO
from pyro.optim import Adam


def beta_bernoulli_demo(num_obs=50, true_p=0.7):
    """Return approximate alpha, beta for a coin with unknown bias."""
    observations = torch.bernoulli(torch.full((num_obs,), true_p))

    # Model: p ~ Beta(1,1); data ~ Bernoulli(p)
    def model(data):
        p = pyro.sample("p", dist.Beta(1.0, 1.0))
        with pyro.plate("data", data.size(0)):
            pyro.sample("obs", dist.Bernoulli(p), obs=data)

    # Guide: q(p) ~ Beta(alpha, beta)
    def guide(data):
        alpha = pyro.param("alpha", torch.tensor(1.0),
                           constraint=dist.constraints.positive)
        beta = pyro.param("beta", torch.tensor(1.0),
                          constraint=dist.constraints.positive)
        pyro.sample("p", dist.Beta(alpha, beta))

    svi = SVI(model, guide, Adam({"lr": 0.05}), Trace_ELBO())

    for step in range(20):
        loss = svi.step(observations)
        if step % 5 == 0:
            print(f"SVI step {step:02d}, ELBO = {loss:.2f}")

    alpha = pyro.param("alpha").item()
    beta  = pyro.param("beta").item()
    est_p = alpha / (alpha + beta)
    return alpha, beta, est_p

def main() :

    print("Hello from trajectoire-pyro!")

    # ---------------------------------------------------------------------
    # 1. Environment report
    # ---------------------------------------------------------------------
    print("=== Runtime ===")
    print(f"Python     : {sys.version.split()[0]}")
    print(f"Platform   : {platform.platform()}")
    print(f"Torch      : {torch.__version__}")
    print(f"Pyro       : {pyro.__version__}")
    device = ("mps" if torch.backends.mps.is_available()
              else "cuda" if torch.cuda.is_available()
              else "cpu")
    print(f"Device     : {device}")
    print()

    # ---------------------------------------------------------------------
    # 2. Tiny Pyro job
    # ---------------------------------------------------------------------
    print("Running Beta–Bernoulli demo…")
    a, b, p_hat = beta_bernoulli_demo()
    print(f"\nPosterior alpha={a:.2f}, beta={b:.2f} → mean={p_hat:.3f}")

    # Simple sanity check: recovered p should be within 0.1 of true 0.7
    assert math.isclose(p_hat, 0.7, abs_tol=0.1), "Pyro inference looks wrong!"

    print("\n✅  Environment looks good — container is ready for AutoGen.\n")

if __name__ == "__main__":
    main()