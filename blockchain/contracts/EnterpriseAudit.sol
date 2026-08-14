// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title EnterpriseAudit
 * @dev Stores critical workflow audit events on-chain for immutability.
 * Currently a starter implementation. Not deployed to Polygon yet.
 */
contract EnterpriseAudit {
    struct AuditEvent {
        string orderId;
        string eventType;
        string eventHash;
        uint256 timestamp;
        string actor;
    }

    // Mapping from Order ID to an array of Audit Events
    mapping(string => AuditEvent[]) public orderAuditTrails;

    event AuditEventRecorded(
        string indexed orderId,
        string eventType,
        string eventHash,
        uint256 timestamp,
        string actor
    );

    /**
     * @dev Record a new audit event for a specific order workflow.
     */
    function recordEvent(
        string memory _orderId,
        string memory _eventType,
        string memory _eventHash,
        string memory _actor
    ) public {
        AuditEvent memory newEvent = AuditEvent({
            orderId: _orderId,
            eventType: _eventType,
            eventHash: _eventHash,
            timestamp: block.timestamp,
            actor: _actor
        });

        orderAuditTrails[_orderId].push(newEvent);

        emit AuditEventRecorded(
            _orderId,
            _eventType,
            _eventHash,
            block.timestamp,
            _actor
        );
    }

    /**
     * @dev Retrieve all audit events for a given order ID.
     */
    function getAuditTrail(string memory _orderId) public view returns (AuditEvent[] memory) {
        return orderAuditTrails[_orderId];
    }
}
