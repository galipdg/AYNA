package com.ayna.server.repository;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import org.junit.jupiter.api.Test;

import com.ayna.server.repository.GridColumns.Child;

/** The header rules of {@link GridColumns} on the tree shapes measured in `eval/spikes/grid-probes.md`. */
class GridColumnsTest {

	private static Child child(long index, String controlType, String name, List<Long> bounds, List<Child> items) {
		return new Child(index, controlType, name, bounds, items);
	}

	private static Child child(long index, String controlType, String name, List<Long> bounds) {
		return child(index, controlType, name, bounds, List.of());
	}

	private static Child item(long index, String name) {
		return child(index, "HeaderItem", name, null);
	}

	/** KeePass 2's entry list: a Header with five HeaderItems, then one ListItem per entry. */
	@Test
	void aHeaderChildGivesItsHeaderItemsInOrder() {
		Child header = child(0, "Header", "Header Control", null, List.of(item(3, "URL"), item(0, "Title"),
				item(1, "User Name"), item(4, "Notes"), item(2, "Password")));
		List<Child> children = List.of(header, child(1, "ListItem", "Sample Entry", null),
				child(2, "ListItem", "Sample Entry #2", null));

		assertThat(GridColumns.of("List", children)).containsExactly("Title", "User Name", "Password", "URL", "Notes");
	}

	/**
	 * Qt's `QTableWidget`: a corner Pane, the column Headers, then per row a row Header (`1`, …)
	 * left of that row's DataItems; the row headers are not columns.
	 */
	@Test
	void directHeadersBeforeTheFirstCellAreTheColumnsWithoutTheRowHeaders() {
		List<Child> children = new ArrayList<>(List.of(child(0, "Pane", null, List.of(10L, 10L, 40L, 30L)),
				child(1, "Header", "Ad", List.of(40L, 10L, 140L, 30L)),
				child(2, "Header", "Soyad", List.of(140L, 10L, 240L, 30L)),
				child(3, "Header", "Şehir", List.of(240L, 10L, 340L, 30L)),
				child(4, "Header", "1", List.of(10L, 30L, 40L, 50L)),
				child(5, "DataItem", "Ayşe", List.of(40L, 30L, 140L, 50L)),
				child(6, "DataItem", "Yılmaz", List.of(140L, 30L, 240L, 50L)),
				child(7, "DataItem", "Ankara", List.of(240L, 30L, 340L, 50L)),
				child(8, "Header", "2", List.of(10L, 50L, 40L, 70L)),
				child(9, "DataItem", "Mehmet", List.of(40L, 50L, 140L, 70L))));
		Collections.reverse(children);

		assertThat(GridColumns.of("Table", children)).containsExactly("Ad", "Soyad", "Şehir");
	}

	/** A Qt table whose horizontal header is hidden shows only row headers: no columns, not `1`. */
	@Test
	void onlyRowHeadersGiveNoColumns() {
		List<Child> children = List.of(child(0, "Header", "1", List.of(10L, 30L, 40L, 50L)),
				child(1, "DataItem", "Ayşe", List.of(40L, 30L, 140L, 50L)));

		assertThat(GridColumns.of("Table", children)).isEmpty();
	}

	/** An empty Qt table reports no headers ([8] in the v0.2 ADR); a grid with no Header gives none either. */
	@Test
	void noHeadersGiveAnEmptyList() {
		assertThat(GridColumns.of("Table", List.of())).isEmpty();
		assertThat(GridColumns.of("DataGrid", List.of(child(0, "DataItem", "a", null), child(1, "DataItem", "b", null))))
			.isEmpty();
	}

	/** A List's Header is a container: with its items scrolled out, its own name is no column. */
	@Test
	void aListUsesOnlyItsHeaderItems() {
		List<Child> children = List.of(child(0, "Header", "Header Control", null), child(1, "ListItem", "a", null));

		assertThat(GridColumns.of("List", children)).isEmpty();
		assertThat(GridColumns.of("Table", List.of(child(0, "HeaderItem", "Name", null)))).containsExactly("Name");
	}

	@Test
	void blankAndRepeatedNamesAreLeftOut() {
		Child header = child(0, "Header", null, null,
				List.of(item(0, "Title"), item(1, null), item(2, " "), item(3, "Title"), item(4, "URL")));

		assertThat(GridColumns.of("List", List.of(header))).containsExactly("Title", "URL");
	}

	/** A Header whose items are all unnamed does not hide direct headers; missing bounds keep a header. */
	@Test
	void anEmptyHeaderFallsBackToTheDirectHeaders() {
		Child header = child(0, "Header", null, null, List.of(item(0, null)));
		List<Child> children = List.of(header, child(1, "HeaderItem", "Name", null), child(2, "DataItem", "x", null));

		assertThat(GridColumns.of("DataGrid", children)).containsExactly("Name");
	}

}
