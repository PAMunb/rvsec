import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.commands.command_exception import CommandException
from rv_monitor_generator.config import RVGeneratorConfig
from rv_monitor_generator.runtime_verification_generator import (
    RuntimeVerificationGenerator,
)


class TestRuntimeVerificationGeneratorComplete:
    """
    Complete test coverage for RuntimeVerificationGenerator including edge cases and error conditions.

    This test suite ensures 100% coverage of all methods including private methods,
    error handling scenarios, and integration with real MOP specifications.
    """

    @pytest.fixture
    def temp_environment_with_real_specs(self):
        """Create temporary directory structure with real JCA MOP specifications."""
        temp_dir = tempfile.mkdtemp()

        # Create mock RVSEC structure with real specs
        rvsec_structure = {
            "javamop/bin": ["javamop"],
            "rv-monitor/bin": ["rv-monitor"],
            "rvsec/rvsec-mop/src/main/resources/jca": [
                "MessageDigestSpec.mop",
                "SecureRandomSpec.mop",
            ],
            "rvsec/rvsec-mop/src/main/resources/generic": ["IteratorSpec.mop"],
            "rvsec/rvsec-mop/src/main/resources/aspect": ["logging.aj", "coverage.aj"],
        }

        for dir_path, files in rvsec_structure.items():
            full_dir = os.path.join(temp_dir, dir_path)
            os.makedirs(full_dir, exist_ok=True)

            for file_name in files:
                file_path = os.path.join(full_dir, file_name)
                with open(file_path, "w") as f:
                    if file_name == "MessageDigestSpec.mop":
                        f.write(self._get_message_digest_spec())
                    elif file_name == "SecureRandomSpec.mop":
                        f.write(self._get_secure_random_spec())
                    elif file_name == "IteratorSpec.mop":
                        f.write(self._get_iterator_spec())
                    elif file_name.endswith(".aj"):
                        f.write(self._get_aspectj_content(file_name))
                    else:
                        f.write('#!/bin/bash\necho "Mock tool execution"')

                # Make binaries executable
                if dir_path.endswith("/bin"):
                    os.chmod(file_path, 0o755)

        yield temp_dir
        shutil.rmtree(temp_dir)

    def _get_message_digest_spec(self):
        """Return real MessageDigest MOP specification content."""
        return """package mop;

import java.security.Provider;
import java.security.MessageDigest;
import java.util.List;

import br.unb.cic.mop.eh.*;
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;

// The MessageDigestSpec specifies
// the correct usage of the MessageDigest
// class (from the JCA specification).
MessageDigestSpec(MessageDigest digest) {

    List<String> algorithms = Arrays.asList("SHA-256", "SHA-384", "SHA-512", "SHA256", "SHA384", "SHA512");
    MessageDigest md = null;
	String currentAlgorithmInstance = "";

	/*
	getInstance events should not, by themselves, trigger UnsalfeAlgorithm errors. The reason is because the algorithm
	is only actually executed during the encryption phase (i.e., in calls to digest() and update(), in the case of MD.)
	Therefore, during the getInstance sub-graph, we only need to keep track of what is the latest algorithm that has
	been instantiated.
	We can use ExecutionContext to keep track of a propety UNSAFE_ALGORITHM, but it is working as is.
	 */
	event g1 after(String alg) returning(MessageDigest digest):
	  call(public static MessageDigest MessageDigest.getInstance(String))
	  && args(alg) && condition(algorithms.contains(alg.toUpperCase())) {
	  md = digest;
	  currentAlgorithmInstance = alg;
	}

	event g2 after(String alg, String provider) returning(MessageDigest digest):
      call(public static MessageDigest MessageDigest.getInstance(String, String))
      && args(alg, provider) && condition(algorithms.contains(alg.toUpperCase())) {
      md = digest;
	  currentAlgorithmInstance = alg;
    }

    event g3 after(String alg, Provider provider) returning(MessageDigest digest):
      call(public static MessageDigest MessageDigest.getInstance(String, Provider))
      && args(alg, provider) && condition(algorithms.contains(alg.toUpperCase())) {
        md = digest;
    	currentAlgorithmInstance = alg;
    }

	/*
	We no longer throw errors after unsafe instantiation events, otherwise we would throw InvalidSequenceOfMethodCalls
	in cases like (g3* g1 | g3* g2).
	Not throwing here eliminates the InvalidSequenceOfMethodCalls false positive in bench02.BrokenHashABPSCase1
	 */
	event g4 after(String alg) returning(MessageDigest digest):
	  call(public static MessageDigest MessageDigest.getInstance(String))
    	  && args(alg) && condition(!algorithms.contains(currentAlgorithmInstance.toUpperCase()))
        {
//          ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", "" + __LOC,
//             "expecting one of {SHA-256, SHA-384, SHA-512} but found " + alg + "."));
		    currentAlgorithmInstance = alg;
        }

	/*
	It's inside the events that actually consume the algorithm that we catch UnsafeAlgorithm
	 */
	event update after(MessageDigest digest):
	  call(void MessageDigest.update(..)) &&
	  target(digest) {
		if (!algorithms.contains(currentAlgorithmInstance.toUpperCase())) {
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", "" +
		__LOC,"expecting one of {SHA-256, SHA-384, SHA-512} but found " + currentAlgorithmInstance + "."));
		}
	  }

	event reset before(MessageDigest digest):
	  call(void MessageDigest.reset()) &&
	  target(digest) { }

	event d1 after(MessageDigest digest) returning(byte[] out):
	 call(public byte[] MessageDigest.digest()) &&
	 target(digest) {
	    ExecutionContext.instance().setProperty(Property.DIGESTED, out);
	}

	/*
	Same case as update
	 */
	event d2 after(MessageDigest digest) returning(byte[] out):
     call(public byte[] MessageDigest.digest(byte[])) &&
     target(digest) {
		if (!algorithms.contains(currentAlgorithmInstance.toUpperCase())) {
			ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", "" +
		     __LOC, "expecting one of {SHA-256, SHA-384, SHA-512} but found " + currentAlgorithmInstance + "."));
		}
    	ExecutionContext.instance().setProperty(Property.DIGESTED, out);
    }

    event d3 after(byte[] out, int offset, int len, MessageDigest digest):
     call(public int MessageDigest.digest(byte[], int, int)) &&
     args(out, offset, len) &&
     target(digest) {
       ExecutionContext.instance().setProperty(Property.DIGESTED, out);
    }

	/*
	Allowing g3 followed by g1 or g2 will eliminate the Invalid SequenceOfMethodCalls false positive in
	bench02.BrokenHashABPSCase1
	*/
	ere : (g4* g1 | g4* g2 | g4* g3) (d2 | (update+ (d1 | d2 | d3)))+

	@fail {
           ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "MessageDigestSpec",  "" + __LOC));
           ExecutionContext.instance().unsetObjectAsInAcceptingState(md);
           __RESET;
	}

	@match {
           ExecutionContext.instance().setObjectAsInAcceptingState(md);
	}
}
"""

    def _get_secure_random_spec(self):
        """Return real SecureRandom MOP specification content."""
        return """package mop;

import java.security.SecureRandom;
import java.util.stream.IntStream;

import br.unb.cic.mop.eh.*;
import br.unb.cic.mop.ExecutionContext;
import br.unb.cic.mop.Property;

SecureRandomSpec(SecureRandom r) {

    SecureRandom sr;
    List<String> algorithms = Arrays.asList("SHA1PRNG", "Windows-PRNG", "NativePRNG",
        "NativePRNGBlocking", "NativePRNGNonBlocking", "PKCS11");

    event c1 after() returning(SecureRandom r):
      call(public SecureRandom.new()) {
        sr = r;
    }

    event g1 after(String alg) returning(SecureRandom r):
      call(public static SecureRandom SecureRandom.getInstance(String))
      && args(alg)
      && condition(algorithms.contains(alg)) {
       sr = r;
    }

    event g4 after(String alg) returning(SecureRandom r):
      call(public static SecureRandom SecureRandom.getInstance(String, ..))
      && args(alg)
      && condition(!algorithms.contains(alg)) {
        ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "SecureRandomSpec", "" + __LOC,
         "expecting one of " + String.join(" or ", algorithms) + " but found " + alg + "."));
    }

    event next1 before(SecureRandom r, int randIntInRange):
      call(public int SecureRandom.nextInt(int))
      && args(randIntInRange)
      && target(r) {
         ExecutionContext.instance().setProperty(Property.RANDOMIZED, randIntInRange);
    }

    fsm :
      start [
         c1 -> init
         g1 -> init
      ]
      init [
         next1 -> end
      ]
      end [
         next1 -> end
      ]

    @fail {
      ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "SecureRandomSpec", "" + __LOC));
      __RESET;
    }

    @match {
        ExecutionContext.instance().setObjectAsInAcceptingState(sr);
        ExecutionContext.instance().setProperty(Property.RANDOMIZED, sr);
    }
}
"""

    def _get_iterator_spec(self):
        """Return generic Iterator MOP specification content."""
        return """package mop;

import java.util.*;

import br.unb.cic.mop.eh.*;

IteratorSpec(Iterator i) {

    event hasnext after(Iterator i) returning(boolean b):
        call(* Iterator.hasNext()) && target(i) {}

    event next after(Iterator i):
        call(* Iterator.next()) && target(i) {}

    ere : hasnext* next (hasnext* next)*

    @fail {
        ErrorCollector.instance().addError(new ErrorDescription(ErrorType.InvalidSequenceOfMethodCalls, "IteratorSpec", "" + __LOC));
    }
}
"""

    def _get_aspectj_content(self, filename):
        """Return AspectJ file content."""
        if filename == "logging.aj":
            return """// Logging AspectJ file for monitored operations
public aspect LoggingAspect {
    pointcut monitoredMethods(): execution(* *.*(..));
    
    before(): monitoredMethods() {
        System.out.println("Method called: " + thisJoinPoint.getSignature());
    }
}
"""
        elif filename == "coverage.aj":
            return """// Coverage AspectJ file for monitored operations
public aspect CoverageAspect {
    pointcut trackedMethods(): execution(* java.security.*.*(..));
    
    after(): trackedMethods() {
        System.out.println("JCA method executed: " + thisJoinPoint.getSignature());
    }
}
"""
        return f"// Generic AspectJ file: {filename}"

    def test_execute_javamop_detailed(self, temp_environment_with_real_specs):
        """Test _execute_javamop method with detailed verification."""
        config = RVGeneratorConfig(
            rvsec_root=temp_environment_with_real_specs,
            mop_specs_dir=os.path.join(
                temp_environment_with_real_specs,
                "rvsec/rvsec-mop/src/main/resources/jca",
            ),
        )

        output_dir = tempfile.mkdtemp()

        try:
            with patch(
                "rv_monitor_generator.runtime_verification_generator.LoggingManager"
            ) as mock_logging_mgr, patch(
                "rv_monitor_generator.runtime_verification_generator.ErrorHandler"
            ) as mock_error_handler, patch(
                "rv_android_core.util.utils.execute_command"
            ) as mock_execute, patch(
                "rv_android_core.util.utils.move_files_by_extension"
            ) as mock_move, patch(
                "rv_android_core.util.utils.copy_files_by_extension"
            ) as mock_copy:

                # Setup mocks
                mock_logger = MagicMock()
                mock_logging_mgr.get_instance.return_value.get_logger.return_value = (
                    mock_logger
                )
                mock_error_handler.get_instance.return_value = MagicMock()

                # Initialize generator
                generator = RuntimeVerificationGenerator(config)

                # Execute JavaMOP step
                generator._execute_javamop(output_dir)

                # Verify JavaMOP command execution
                mock_execute.assert_called_once()
                command_args = mock_execute.call_args[0]
                assert command_args[1] == "javamop"

                # Verify command contains expected arguments
                command = command_args[0]
                # The binary path is not in args, it's the command itself
                assert "-d" in command.args
                assert output_dir in command.args
                assert "-merge" in command.args
                # Verify the mop specs pattern is included
                assert any(".mop" in arg for arg in command.args)

                # Verify file operations
                mock_move.assert_called_once()
                mock_copy.assert_called_once()

                # Verify logging
                assert mock_logger.info.call_count >= 1
                assert mock_logger.debug.call_count >= 1

        finally:
            shutil.rmtree(output_dir)

    def test_execute_rvmonitor_detailed(self, temp_environment_with_real_specs):
        """Test _execute_rvmonitor method with detailed verification."""
        config = RVGeneratorConfig(
            rvsec_root=temp_environment_with_real_specs,
            mop_specs_dir=os.path.join(
                temp_environment_with_real_specs,
                "rvsec/rvsec-mop/src/main/resources/jca",
            ),
        )

        output_dir = tempfile.mkdtemp()

        # Create mock RVM files
        for i in range(3):
            rvm_file = os.path.join(output_dir, f"Monitor{i}.rvm")
            with open(rvm_file, "w") as f:
                f.write(f"// Mock RVM file {i}")

        try:
            with patch(
                "rv_monitor_generator.runtime_verification_generator.LoggingManager"
            ) as mock_logging_mgr, patch(
                "rv_monitor_generator.runtime_verification_generator.ErrorHandler"
            ) as mock_error_handler, patch(
                "rv_android_core.util.utils.execute_command"
            ) as mock_execute, patch(
                "rv_android_core.util.utils.delete_files_by_extension"
            ) as mock_delete:

                # Setup mocks
                mock_logger = MagicMock()
                mock_logging_mgr.get_instance.return_value.get_logger.return_value = (
                    mock_logger
                )
                mock_error_handler.get_instance.return_value = MagicMock()

                # Initialize generator
                generator = RuntimeVerificationGenerator(config)

                # Execute RV-Monitor step
                generator._execute_rvmonitor(output_dir)

                # Verify RV-Monitor command execution
                mock_execute.assert_called_once()
                command_args = mock_execute.call_args[0]
                assert command_args[1] == "rvmonitor"

                # Verify command contains expected arguments
                command = command_args[0]
                # The binary path is not in args, it's the command itself
                assert "-d" in command.args
                assert output_dir in command.args
                assert "-merge" in command.args
                # Verify the rvm pattern is included
                assert any(".rvm" in arg for arg in command.args)

                # Verify cleanup
                mock_delete.assert_called_once()
                delete_args = mock_delete.call_args[0]
                assert ".rvm" in delete_args
                assert output_dir in delete_args

        finally:
            shutil.rmtree(output_dir)

    def test_command_exception_handling_in_javamop(
        self, temp_environment_with_real_specs
    ):
        """Test CommandException handling in _execute_javamop."""
        config = RVGeneratorConfig(
            rvsec_root=temp_environment_with_real_specs,
            mop_specs_dir=os.path.join(
                temp_environment_with_real_specs,
                "rvsec/rvsec-mop/src/main/resources/jca",
            ),
        )

        output_dir = tempfile.mkdtemp()

        try:
            with patch(
                "rv_monitor_generator.runtime_verification_generator.LoggingManager"
            ) as mock_logging_mgr, patch(
                "rv_monitor_generator.runtime_verification_generator.ErrorHandler"
            ) as mock_error_handler, patch(
                "rv_android_core.util.utils.execute_command"
            ) as mock_execute:

                # Setup mocks
                mock_logger = MagicMock()
                mock_logging_mgr.get_instance.return_value.get_logger.return_value = (
                    mock_logger
                )
                mock_error_handler_instance = MagicMock()
                mock_error_handler.get_instance.return_value = (
                    mock_error_handler_instance
                )

                # Configure exception
                mock_execute.side_effect = CommandException(
                    "javamop", 1, "Syntax error in MOP specification"
                )

                # Initialize generator
                generator = RuntimeVerificationGenerator(config)

                # Test that exception propagates
                with pytest.raises(CommandException):
                    generator._execute_javamop(output_dir)

        finally:
            shutil.rmtree(output_dir)

    def test_command_exception_handling_in_rvmonitor(
        self, temp_environment_with_real_specs
    ):
        """Test CommandException handling in _execute_rvmonitor."""
        config = RVGeneratorConfig(
            rvsec_root=temp_environment_with_real_specs,
            mop_specs_dir=os.path.join(
                temp_environment_with_real_specs,
                "rvsec/rvsec-mop/src/main/resources/jca",
            ),
        )

        output_dir = tempfile.mkdtemp()

        try:
            with patch(
                "rv_monitor_generator.runtime_verification_generator.LoggingManager"
            ) as mock_logging_mgr, patch(
                "rv_monitor_generator.runtime_verification_generator.ErrorHandler"
            ) as mock_error_handler, patch(
                "rv_android_core.util.utils.execute_command"
            ) as mock_execute:

                # Setup mocks
                mock_logger = MagicMock()
                mock_logging_mgr.get_instance.return_value.get_logger.return_value = (
                    mock_logger
                )
                mock_error_handler_instance = MagicMock()
                mock_error_handler.get_instance.return_value = (
                    mock_error_handler_instance
                )

                # Configure exception
                mock_execute.side_effect = CommandException(
                    "rvmonitor", 1, "Failed to generate monitors"
                )

                # Initialize generator
                generator = RuntimeVerificationGenerator(config)

                # Test that exception propagates
                with pytest.raises(CommandException):
                    generator._execute_rvmonitor(output_dir)

        finally:
            shutil.rmtree(output_dir)

    def test_get_generation_summary_comprehensive(
        self, temp_environment_with_real_specs
    ):
        """Test get_generation_summary with comprehensive artifact types."""
        config = RVGeneratorConfig(
            rvsec_root=temp_environment_with_real_specs,
            mop_specs_dir=os.path.join(
                temp_environment_with_real_specs,
                "rvsec/rvsec-mop/src/main/resources/jca",
            ),
        )

        output_dir = tempfile.mkdtemp()

        try:
            # Create comprehensive set of generated files
            generated_files = [
                ("MessageDigestMonitor.aj", "// Generated MessageDigest AspectJ"),
                ("SecureRandomMonitor.aj", "// Generated SecureRandom AspectJ"),
                ("LoggingAspect.aj", "// Custom logging AspectJ"),
                (
                    "MessageDigestMonitor.java",
                    "// Generated MessageDigest monitor class",
                ),
                ("SecureRandomMonitor.java", "// Generated SecureRandom monitor class"),
                ("MonitorUtils.java", "// Generated utility class"),
                ("README.txt", "// Documentation file - should not be counted"),
            ]

            for filename, content in generated_files:
                with open(os.path.join(output_dir, filename), "w") as f:
                    f.write(content)

            with patch(
                "rv_monitor_generator.runtime_verification_generator.LoggingManager"
            ) as mock_logging_mgr, patch(
                "rv_monitor_generator.runtime_verification_generator.ErrorHandler"
            ) as mock_error_handler:

                # Setup mocks
                mock_logger = MagicMock()
                mock_logging_mgr.get_instance.return_value.get_logger.return_value = (
                    mock_logger
                )
                mock_error_handler.get_instance.return_value = MagicMock()

                # Initialize generator
                generator = RuntimeVerificationGenerator(config)

                # Get summary
                summary = generator.get_generation_summary(output_dir)

                # Verify summary structure
                assert "output_directory" in summary
                assert "aspectj_files" in summary
                assert "monitor_classes" in summary
                assert "specs_processed" in summary

                # Verify counts
                assert summary["aspectj_files"] == 3  # .aj files only
                assert summary["monitor_classes"] == 3  # .java files only
                assert (
                    summary["specs_processed"]["count"] == 2
                )  # MessageDigest + SecureRandom

                # Verify specs info
                assert (
                    summary["specs_processed"]["source_directory"]
                    == config.mop_specs_dir
                )

        finally:
            shutil.rmtree(output_dir)

    def test_mop_specs_discovery_with_real_specs(
        self, temp_environment_with_real_specs
    ):
        """Test _get_mop_specs with real JCA specifications."""
        config = RVGeneratorConfig(
            rvsec_root=temp_environment_with_real_specs,
            mop_specs_dir=os.path.join(
                temp_environment_with_real_specs,
                "rvsec/rvsec-mop/src/main/resources/jca",
            ),
        )

        with patch(
            "rv_monitor_generator.runtime_verification_generator.LoggingManager"
        ) as mock_logging_mgr, patch(
            "rv_monitor_generator.runtime_verification_generator.ErrorHandler"
        ) as mock_error_handler:

            # Setup mocks
            mock_logger = MagicMock()
            mock_logging_mgr.get_instance.return_value.get_logger.return_value = (
                mock_logger
            )
            mock_error_handler.get_instance.return_value = MagicMock()

            # Initialize generator
            generator = RuntimeVerificationGenerator(config)

            # Test spec discovery
            specs = generator._get_mop_specs()

            # Verify specs found
            assert len(specs) == 2  # MessageDigestSpec.mop and SecureRandomSpec.mop
            assert all(spec.endswith(".mop") for spec in specs)
            assert any("MessageDigestSpec.mop" in spec for spec in specs)
            assert any("SecureRandomSpec.mop" in spec for spec in specs)

    def test_generic_specs_discovery(self, temp_environment_with_real_specs):
        """Test spec discovery with generic (non-JCA) specifications."""
        config = RVGeneratorConfig(
            rvsec_root=temp_environment_with_real_specs,
            mop_specs_dir=os.path.join(
                temp_environment_with_real_specs,
                "rvsec/rvsec-mop/src/main/resources/generic",
            ),
        )

        with patch(
            "rv_monitor_generator.runtime_verification_generator.LoggingManager"
        ) as mock_logging_mgr, patch(
            "rv_monitor_generator.runtime_verification_generator.ErrorHandler"
        ) as mock_error_handler:

            # Setup mocks
            mock_logger = MagicMock()
            mock_logging_mgr.get_instance.return_value.get_logger.return_value = (
                mock_logger
            )
            mock_error_handler.get_instance.return_value = MagicMock()

            # Initialize generator
            generator = RuntimeVerificationGenerator(config)

            # Test spec discovery
            specs = generator._get_mop_specs()

            # Verify generic specs found
            assert len(specs) == 1  # IteratorSpec.mop
            assert all(spec.endswith(".mop") for spec in specs)
            assert any("IteratorSpec.mop" in spec for spec in specs)

    def test_error_handling_chain_integration(self, temp_environment_with_real_specs):
        """Test complete error handling chain integration."""
        config = RVGeneratorConfig(
            rvsec_root=temp_environment_with_real_specs,
            mop_specs_dir=os.path.join(
                temp_environment_with_real_specs,
                "rvsec/rvsec-mop/src/main/resources/jca",
            ),
        )

        output_dir = tempfile.mkdtemp()

        try:
            with patch(
                "rv_monitor_generator.runtime_verification_generator.LoggingManager"
            ) as mock_logging_mgr, patch(
                "rv_monitor_generator.runtime_verification_generator.ErrorHandler"
            ) as mock_error_handler, patch(
                "rv_android_core.util.utils.reset_folder"
            ) as mock_reset:

                # Setup mocks
                mock_logger = MagicMock()
                mock_logging_mgr.get_instance.return_value.get_logger.return_value = (
                    mock_logger
                )
                mock_error_handler_instance = MagicMock()
                mock_error_handler.get_instance.return_value = (
                    mock_error_handler_instance
                )

                # Configure exception in early stage
                mock_reset.side_effect = OSError("Permission denied")

                # Initialize generator
                generator = RuntimeVerificationGenerator(config)

                # Execute and verify error handling
                result = generator.generate_monitors(output_dir)

                # Verify failure result
                assert result is False

                # Verify error handler was called
                mock_error_handler_instance.handle_error.assert_called_once()
                error_args = mock_error_handler_instance.handle_error.call_args[0]
                assert isinstance(error_args[0], OSError)
                assert isinstance(error_args[1], dict)
                assert "component" in error_args[1]
                assert "operation" in error_args[1]

        finally:
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
