package com.ayna.server.repository;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

import org.neo4j.driver.Value;

/**
 * The column headers of a grid or list target, read from the captured tree (#221): what the
 * editor offers for a `cell` check's column and a row's key column. The captured Elements keep
 * their tree order in `siblingIndex`, so the headers come from the graph and no extra property
 * is stored.
 *
 * Two shapes, both measured (`eval/spikes/grid-probes.md`):
 * <ul>
 * <li>A `Header` child holding `HeaderItem`s (KeePass 2's WinForms list, which has no Table
 * pattern): the HeaderItems' names, in order.</li>
 * <li>Header elements as direct children of a Table or DataGrid (Qt's `QTableWidget`): the
 * target's own Header and HeaderItem children before its first cell, except those that lie
 * wholly left of that cell, which are Qt's row headers (`1`, `2`, …). Not for a List, whose
 * Header child is a container: with no items captured its own name is no column.</li>
 * </ul>
 *
 * The list may be incomplete (a header scrolled out or virtualised, an empty Qt table, a grid
 * with no Header at all), so it is a convenience for the editor, never a list to validate a
 * column against. Blank names are left out and each name appears once.
 */
final class GridColumns {

	/**
	 * A Cypher expression for the children of the Element `e` when it is a grid (the control types
	 * of ADR `2026-10-28-step-schema-v0-2-rows`), each with its HeaderItem children; {@link #of(Value)}
	 * reads it. Empty for any other control type, or when `e` is null.
	 */
	static final String CHILDREN = """
			COLLECT { MATCH (e)-[:CONTAINS]->(c:Element)
			  WHERE e.controlType IN ['DataGrid', 'Table', 'List']
			  RETURN {index: c.siblingIndex, controlType: c.controlType, name: c.name, bounds: c.bounds,
			    items: COLLECT { MATCH (c)-[:CONTAINS]->(i:Element {controlType: 'HeaderItem'})
			      RETURN {index: i.siblingIndex, name: i.name} AS item }} AS child }""";

	private static final Set<String> HEADERS = Set.of("Header", "HeaderItem");

	private static final Set<String> CELLS = Set.of("DataItem", "ListItem");

	private static final Comparator<Child> BY_INDEX = Comparator.comparingLong(Child::index);

	private GridColumns() {
	}

	/** One child of the target: `bounds` is `[left, top, right, bottom]` or null; `items` its HeaderItems. */
	record Child(long index, String controlType, String name, List<Long> bounds, List<Child> items) {
	}

	/** The columns of a target of `controlType` from the result of {@link #CHILDREN}. */
	static List<String> of(String controlType, Value children) {
		return of(controlType, children.asList(GridColumns::child));
	}

	/** The columns of a target of `controlType` with these children, in any order. */
	static List<String> of(String controlType, List<Child> children) {
		List<Child> ordered = children.stream().sorted(BY_INDEX).toList();
		for (Child child : ordered) {
			if ("Header".equals(child.controlType()) && !names(child.items()).isEmpty()) {
				return names(child.items());
			}
		}

		if (!"Table".equals(controlType) && !"DataGrid".equals(controlType)) {
			return List.of();
		}
		Child firstCell = ordered.stream().filter(c -> CELLS.contains(c.controlType())).findFirst().orElse(null);
		List<Child> headers = new ArrayList<>();
		for (Child child : ordered) {
			if (child == firstCell) {
				break;
			}
			if (HEADERS.contains(child.controlType()) && !leftOf(child, firstCell)) {
				headers.add(child);
			}
		}
		return names(headers);
	}

	/** True when `child` ends at or before the left edge of `cell`: a row header beside the rows. */
	private static boolean leftOf(Child child, Child cell) {
		if (cell == null || child.bounds() == null || cell.bounds() == null || child.bounds().size() != 4
				|| cell.bounds().size() != 4) {
			return false;
		}
		return child.bounds().get(2) <= cell.bounds().get(0);
	}

	private static List<String> names(List<Child> children) {
		Set<String> names = new LinkedHashSet<>();
		children.stream()
			.sorted(BY_INDEX)
			.map(Child::name)
			.filter(name -> name != null && !name.isBlank())
			.forEach(names::add);
		return List.copyOf(names);
	}

	private static Child child(Value value) {
		Value bounds = value.get("bounds");
		Value items = value.get("items");
		return new Child(value.get("index").asLong(Long.MAX_VALUE), value.get("controlType").asString(null),
				value.get("name").asString(null), bounds.isNull() ? null : bounds.asList(Value::asLong),
				items.isNull() ? List.of() : items.asList(GridColumns::child));
	}

}
