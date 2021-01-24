defmodule Bowser.MixProject do
  use Mix.Project

  def project do
    [
      app: :bowser,
      version: "0.2.0",
      elixir: "~> 1.9",
      start_permanent: Mix.env() == :prod,
      aliases: [test: "test --no-start"],
      releases: releases(),
      deps: deps(),
      elixirc_options: [
        warnings_as_errors: halt_on_warnings?(Mix.env())
      ]
    ]
  end

  # Run "mix help compile.app" to learn about applications.
  def application do
    [
      extra_applications: extra_applications(Mix.env()),
      mod: {Bowser.Application, []}
    ]
  end

  defp extra_applications(:dev), do: extra_applications(:all) ++ [:remix]
  defp extra_applications(_all), do: [:logger, :nostrum]

  defp halt_on_warnings?(:test), do: false
  defp halt_on_warnings?(_), do: true

  defp releases() do
    [
      bowser: [
        include_executables_for: [:unix]
      ]
    ]
  end

  defp deps do
    [
      {:credo, "~> 1.5.0", only: [:dev, :test], runtime: false},
      {:jason, "~> 1.1"},
      {:mcping, git: "https://github.com/kevinkjt2000/mcping-elixir.git"},
      {:nostrum, "~> 0.4"},
      {:redix, "~> 0.10"},
      {:remix, git: "https://github.com/harlantwood/remix.git", only: :dev}
    ]
  end
end
