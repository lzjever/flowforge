# typed: false
# frozen_string_literal: true

# Routilux Homebrew Formula
# Install with: brew install lzjever/routilux/routilux
# Or: brew tap lzjever/routilux && brew install routilux

class Routilux < Formula
  include Language::Python::Virtualenv

  desc "Event-driven workflow orchestration framework with CLI"
  homepage "https://github.com/lzjever/routilux"
  url "https://files.pythonhosted.org/packages/source/r/routilux/routilux-0.14.0.tar.gz"
  # sha256 "" # Uncomment and add hash after release
  license "Apache-2.0"
  head "https://github.com/lzjever/routilux.git", branch: "main"

  option "without-cli", "Install without CLI dependencies (library only)"

  depends_on "python@3.12" => [:build, :test]

  on_macos do
    on_arm do
      url "https://files.pythonhosted.org/packages/source/r/routilux/routilux-0.14.0.tar.gz"
    end
    on_intel do
      url "https://files.pythonhosted.org/packages/source/r/routilux/routilux-0.14.0.tar.gz"
    end
  end

  on_linux do
    url "https://files.pythonhosted.org/packages/source/r/routilux/routilux-0.14.0.tar.gz"
  end

  def install
    # Install with CLI dependencies by default
    if build.without?("cli")
      odie "Installing without CLI is not yet supported. Please use: pip install routilux"
    end

    virtualenv_install_with_resources
  end

  test do
    # Test CLI is available
    assert_match "routilux", shell_output("#{bin}/routilux --version")

    # Test help command
    assert_match "Usage", shell_output("#{bin}/routilux --help")

    # Test Python import
    system Formula["python@3.12"].opt_libexec/"bin/python", "-c", "import routilux; print(routilux.__version__)"
  end
end
