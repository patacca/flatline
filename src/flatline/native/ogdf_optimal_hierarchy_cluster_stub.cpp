#include <ogdf/layered/OptimalHierarchyClusterLayout.h>

#include <stdexcept>

namespace ogdf {

OptimalHierarchyClusterLayout::OptimalHierarchyClusterLayout()
	: m_nodeDistance(3.0)
	, m_layerDistance(3.0)
	, m_fixedLayerDistance(false)
	, m_weightSegments(2.0)
	, m_weightBalancing(0.1)
	, m_weightClusters(0.05)
	, m_pACGC(nullptr)
	, m_pH(nullptr)
	, m_vertexOffset(0)
	, m_segmentOffset(0)
	, m_clusterLeftOffset(0)
	, m_clusterRightOffset(0) { }

OptimalHierarchyClusterLayout::OptimalHierarchyClusterLayout(
		const OptimalHierarchyClusterLayout& other)
	: HierarchyClusterLayoutModule(other)
	, m_nodeDistance(other.m_nodeDistance)
	, m_layerDistance(other.m_layerDistance)
	, m_fixedLayerDistance(other.m_fixedLayerDistance)
	, m_weightSegments(other.m_weightSegments)
	, m_weightBalancing(other.m_weightBalancing)
	, m_weightClusters(other.m_weightClusters)
	, m_pACGC(nullptr)
	, m_pH(nullptr)
	, m_vertexOffset(0)
	, m_segmentOffset(0)
	, m_clusterLeftOffset(0)
	, m_clusterRightOffset(0) { }

OptimalHierarchyClusterLayout& OptimalHierarchyClusterLayout::operator=(
		const OptimalHierarchyClusterLayout& other) {
	if (this == &other) {
		return *this;
	}

	m_nodeDistance = other.m_nodeDistance;
	m_layerDistance = other.m_layerDistance;
	m_fixedLayerDistance = other.m_fixedLayerDistance;
	m_weightSegments = other.m_weightSegments;
	m_weightBalancing = other.m_weightBalancing;
	m_weightClusters = other.m_weightClusters;
	m_pACGC = nullptr;
	m_pH = nullptr;
	m_vertexOffset = 0;
	m_segmentOffset = 0;
	m_clusterLeftOffset = 0;
	m_clusterRightOffset = 0;
	return *this;
}

void OptimalHierarchyClusterLayout::doCall(
		const ExtendedNestingGraph&, ClusterGraphCopyAttributes&) {
	throw std::logic_error("OptimalHierarchyClusterLayout excluded from no-COIN spike build");
}

} // namespace ogdf
