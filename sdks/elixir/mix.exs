defmodule Fluidian.MixProject do
  use Mix.Project

  def project do
    [
      app: :fluidian,
      version: "1.2.0",
      elixir: "~> 1.12",
      description: "Fluidian SDK for Elixir - build AI-native interfaces.",
      package: [licenses: ["Apache-2.0"], links: %{}],
      deps: []
    ]
  end

  def application, do: [extra_applications: []]
end
