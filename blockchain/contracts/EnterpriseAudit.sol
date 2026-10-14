// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title EnterpriseAudit
 * @dev Immutable on-chain audit anchor registry for the Enterprise AI Control Room.
 *
 * Stores canonical SHA-256 cryptographic digests of critical operational decisions,
 * agent steps, approvals, and actions.
 *
 * Security & Design Principles:
 * 1. Gas efficiency: digests stored as bytes32 rather than arbitrary strings.
 * 2. Privacy & least privilege: confidential business data, pricing, and supplier
 *    identities remain off-chain in PostgreSQL. Only the cryptographic digest, event ID,
 *    event type, and submitter address are published on-chain.
 * 3. Access control: only the authorized contract owner / backend signer can record anchors.
 * 4. Duplicate protection: prevents duplicate anchoring of the same event ID or digest.
 * 5. Independent verification: view functions allow any party to verify off-chain payloads
 *    against the immutable on-chain record without transaction cost.
 */
contract EnterpriseAudit {
    address public owner;

    struct AnchorRecord {
        bytes32 payloadDigest;
        string eventType;
        uint256 blockTimestamp;
        uint256 blockNumber;
        address submitter;
        bool exists;
    }

    struct LegacyAuditEvent {
        string orderId;
        string eventType;
        string eventHash;
        uint256 timestamp;
        string actor;
    }

    // Mapping from event ID to on-chain Anchor Record
    mapping(string => AnchorRecord) private _anchors;

    // Mapping from payload digest to boolean for duplicate digest detection
    mapping(bytes32 => bool) public isDigestAnchored;

    // Legacy mapping from Order ID to array of audit events (backward compatibility)
    mapping(string => LegacyAuditEvent[]) public orderAuditTrails;

    // Events
    event AnchorRecorded(
        string indexed eventId,
        bytes32 indexed payloadDigest,
        string eventType,
        uint256 blockTimestamp,
        uint256 blockNumber,
        address indexed submitter
    );

    event AuditEventRecorded(
        string indexed orderId,
        string eventType,
        string eventHash,
        uint256 timestamp,
        string actor
    );

    event OwnershipTransferred(
        address indexed previousOwner,
        address indexed newOwner
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "EnterpriseAudit: caller is not authorized owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    /**
     * @dev Transfer contract ownership to a new authorized operational signer.
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "EnterpriseAudit: new owner cannot be zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    /**
     * @dev Record a canonical audit event digest on-chain.
     * @param _eventId Unique audit event UUID or batch identifier.
     * @param _eventType High-level event category (e.g., ORDER_APPROVED, ACTION_EXECUTED).
     * @param _payloadDigest 32-byte canonical SHA-256 digest of the event payload.
     * @param _actor Operational actor or agent recording the anchor.
     */
    function recordAnchor(
        string calldata _eventId,
        string calldata _eventType,
        bytes32 _payloadDigest,
        string calldata _actor
    ) external onlyOwner returns (bool) {
        require(bytes(_eventId).length > 0, "EnterpriseAudit: event ID cannot be empty");
        require(_payloadDigest != bytes32(0), "EnterpriseAudit: digest cannot be zero");
        require(!_anchors[_eventId].exists, "EnterpriseAudit: event ID already anchored");
        require(!isDigestAnchored[_payloadDigest], "EnterpriseAudit: payload digest already anchored");

        _anchors[_eventId] = AnchorRecord({
            payloadDigest: _payloadDigest,
            eventType: _eventType,
            blockTimestamp: block.timestamp,
            blockNumber: block.number,
            submitter: msg.sender,
            exists: true
        });

        isDigestAnchored[_payloadDigest] = true;

        emit AnchorRecorded(
            _eventId,
            _payloadDigest,
            _eventType,
            block.timestamp,
            block.number,
            msg.sender
        );

        return true;
    }

    /**
     * @dev Legacy entrypoint: record an event for a specific order workflow.
     * Preserved for backward compatibility with starter contracts.
     */
    function recordEvent(
        string memory _orderId,
        string memory _eventType,
        string memory _eventHash,
        string memory _actor
    ) public onlyOwner {
        LegacyAuditEvent memory newEvent = LegacyAuditEvent({
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
     * @dev Retrieve anchor record for a specific event ID.
     */
    function getAnchor(string calldata _eventId)
        external
        view
        returns (
            bytes32 payloadDigest,
            string memory eventType,
            uint256 blockTimestamp,
            uint256 blockNumber,
            address submitter,
            bool exists
        )
    {
        AnchorRecord memory record = _anchors[_eventId];
        return (
            record.payloadDigest,
            record.eventType,
            record.blockTimestamp,
            record.blockNumber,
            record.submitter,
            record.exists
        );
    }

    /**
     * @dev Independently verify if an expected canonical digest matches the on-chain anchor.
     * @param _eventId The event identifier to verify.
     * @param _expectedDigest The canonical SHA-256 digest computed off-chain.
     * @return matched True if the digest matches the on-chain record exactly.
     * @return blockTimestamp Timestamp of the block where the anchor was committed.
     * @return blockNumber Number of the block where the anchor was committed.
     */
    function verifyAnchor(string calldata _eventId, bytes32 _expectedDigest)
        external
        view
        returns (
            bool matched,
            uint256 blockTimestamp,
            uint256 blockNumber
        )
    {
        AnchorRecord memory record = _anchors[_eventId];
        if (!record.exists) {
            return (false, 0, 0);
        }
        matched = (record.payloadDigest == _expectedDigest);
        return (matched, record.blockTimestamp, record.blockNumber);
    }

    /**
     * @dev Retrieve all legacy audit events for a given order ID.
     */
    function getAuditTrail(string memory _orderId)
        external
        view
        returns (LegacyAuditEvent[] memory)
    {
        return orderAuditTrails[_orderId];
    }
}
