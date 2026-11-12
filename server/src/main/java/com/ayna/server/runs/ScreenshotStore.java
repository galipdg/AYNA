package com.ayna.server.runs;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;
import java.util.stream.Stream;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Step screenshots as PNG files on the server's disk (#51, NFR-40): one folder per run, one file
 * per step, `<runId>/<stepIndex>.png`. The graph keeps only that relative path. Files are written
 * to a temporary name and moved into place, so a reader never sees half a file.
 */
@Component
public class ScreenshotStore {

	private static final Logger log = LoggerFactory.getLogger(ScreenshotStore.class);

	private final Path root;

	public ScreenshotStore(@Value("${ayna.screenshots.dir:data/screenshots}") Path root) {
		this.root = root.toAbsolutePath().normalize();
	}

	/** Where the file of a step goes, relative to the store. */
	static String relativePath(String runId, int stepIndex) {
		return runId + "/" + stepIndex + ".png";
	}

	void write(String relativePath, byte[] png) {
		Path target = resolve(relativePath);
		try {
			Files.createDirectories(target.getParent());
			Path temp = Files.createTempFile(target.getParent(), ".upload-", ".tmp");
			try {
				Files.write(temp, png);
				Files.move(temp, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
			}
			finally {
				Files.deleteIfExists(temp);
			}
		}
		catch (IOException ex) {
			throw new UncheckedIOException("Cannot write screenshot " + relativePath, ex);
		}
	}

	boolean exists(String relativePath) {
		return Files.isRegularFile(resolve(relativePath));
	}

	/** The file's bytes, or null if it is not there. */
	byte[] read(String relativePath) {
		try {
			return Files.readAllBytes(resolve(relativePath));
		}
		catch (NoSuchFileException ex) {
			return null;
		}
		catch (IOException ex) {
			throw new UncheckedIOException("Cannot read screenshot " + relativePath, ex);
		}
	}

	/**
	 * Removes the folders of these runs. A folder that cannot be removed is logged and left for the
	 * next sweep, which removes folders whose run no longer exists ({@link #runFolders()}).
	 */
	public void deleteRuns(Collection<String> runIds) {
		for (String runId : runIds) {
			Path folder = root.resolve(runId).normalize();
			if (!folder.getParent().equals(root) || !Files.isDirectory(folder)) {
				continue;
			}
			try (Stream<Path> files = Files.walk(folder)) {
				for (Path path : files.sorted(Comparator.reverseOrder()).toList()) {
					Files.deleteIfExists(path);
				}
			}
			catch (IOException | UncheckedIOException ex) {
				log.warn("Could not remove the screenshots of run {}; the next sweep tries again", runId, ex);
			}
		}
	}

	/** Run ids that have a folder in the store. Other names in the store are not touched. */
	List<String> runFolders() {
		List<String> ids = new ArrayList<>();
		if (!Files.isDirectory(root)) {
			return ids;
		}
		try (DirectoryStream<Path> folders = Files.newDirectoryStream(root, Files::isDirectory)) {
			for (Path folder : folders) {
				String name = folder.getFileName().toString();
				if (isUuid(name)) {
					ids.add(name);
				}
			}
		}
		catch (IOException ex) {
			throw new UncheckedIOException("Cannot list the screenshot store " + root, ex);
		}
		return ids;
	}

	/** Only paths inside the store, so a stored path can never point elsewhere. */
	private Path resolve(String relativePath) {
		Path path = root.resolve(relativePath).normalize();
		if (!path.startsWith(root) || path.equals(root)) {
			throw new IllegalArgumentException("Screenshot path outside the store: " + relativePath);
		}
		return path;
	}

	private static boolean isUuid(String name) {
		try {
			return UUID.fromString(name).toString().equals(name);
		}
		catch (IllegalArgumentException ex) {
			return false;
		}
	}

}
